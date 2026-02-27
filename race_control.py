"""
Race Control System
Manages live race timing from LLRP reader and manual input
"""
from datetime import datetime, timedelta
from models import TimeRecord, RaceResult, TimingSource, ParticipantStatus, race_participants, Race, TimingPoint, StartMode, Participant
from database import get_session
from race_manager import RaceManager, ParticipantManager
from reader import LLRPReader
from tag_detection import TagDetectionManager
import json
from sqlalchemy import and_


class RaceControl:
    """Controls live race timing"""
    
    def __init__(self, race_id):
        self.race_id = race_id
        self.active = False
        
        # Initialize tag detection manager
        self.tag_detection_manager = TagDetectionManager()
        self._configure_detection_modes()
        
        # Verify race exists
        session = get_session()
        race = session.query(Race).filter(Race.id == race_id).first()
        if not race:
            raise ValueError(f"Race {race_id} not found")
        # We don't keep the race object or session
    
    def _configure_detection_modes(self):
        """Configure detection modes for all timing points in this race"""
        session = get_session()
        timing_points = session.query(TimingPoint).filter(
            TimingPoint.race_id == self.race_id
        ).all()
        
        for tp in timing_points:
            # Configure each timing point with its detection mode
            detection_mode = tp.detection_mode.value if tp.detection_mode else "first_seen"
            window_seconds = tp.detection_window_seconds if tp.detection_window_seconds else 3.0
            
            # Create callback for this timing point
            def make_callback(timing_point_id):
                def callback(epc, timestamp, rssi, mode):
                    print(f"Tag detection finalized: {epc} at timing point {timing_point_id} using {mode} mode (RSSI: {rssi})")
                return callback
            
            self.tag_detection_manager.configure_timing_point(
                tp.id,
                detection_mode,
                window_seconds,
                make_callback(tp.id)
            )
    
    def start_timing(self):
        """Start accepting timing events"""
        self.active = True
        print(f"Race {self.race_id} timing started")
    
    def stop_timing(self):
        """Stop accepting timing events"""
        self.active = False
        print(f"Race {self.race_id} timing stopped")
    
    def process_tag_read(self, epc, timestamp, station_id=None, rssi=None):
        """Handle tag read from external source (LLRP service)"""
        if not self.active:
            return
        
        # MULTI-RACE SUPPORT: Filter tag reads by station assignment
        # Only process tags from LLRP stations assigned to this race's timing points
        timing_point = None
        if station_id is not None:
            session = get_session()
            # Check if this station is assigned to any timing point in this race
            timing_point = session.query(TimingPoint).filter(
                and_(
                    TimingPoint.race_id == self.race_id,
                    TimingPoint.llrp_station_id == station_id
                )
            ).first()
            
            if not timing_point:
                # This tag read is from a station not assigned to this race
                # Silently ignore (it's likely for another race)
                return
        
        # Process through detection manager if we have a timing point
        if timing_point:
            # Use detection manager to buffer and process the read
            result = self.tag_detection_manager.process_tag_read(
                timing_point.id,
                epc,
                rssi if rssi is not None else -50.0,  # Default RSSI if not provided
                timestamp
            )
            
            # If detection is finalized, process it
            if result:
                final_epc, final_timestamp, final_rssi = result
                self._process_finalized_tag(final_epc, final_timestamp, station_id, final_rssi)
            return
    
    def _process_finalized_tag(self, epc, timestamp, station_id=None, rssi=None):
        """Process a finalized tag detection (after detection mode processing)"""
        participant_manager = ParticipantManager()
        # Find participant by RFID tag
        participant = participant_manager.get_participant_by_rfid(epc)
        
        if not participant:
            # print(f"Unknown tag: {epc}") # Optional: reduce log noise
            return
        
        # Check if this is a chip start race
        race_manager = RaceManager()
        race = race_manager.get_race(self.race_id)
        
        if race.start_mode == StartMode.CHIP_START:
            # For chip start, check if this is the participant's first read
            session = get_session()
            existing_records = session.query(TimeRecord).filter(
                TimeRecord.race_id == self.race_id,
                TimeRecord.participant_id == participant.id
            ).count()
            
            if existing_records == 0:
                # This is the first read - create a Start time record
                start_timing_point = session.query(TimingPoint).filter(
                    TimingPoint.race_id == self.race_id,
                    TimingPoint.is_start == True
                ).first()
                
                if start_timing_point:
                    # Convert timestamp to datetime if needed
                    if isinstance(timestamp, (int, float)):
                        dt_timestamp = datetime.fromtimestamp(timestamp)
                    else:
                        dt_timestamp = timestamp
                    
                    # Record the start time
                    self.record_time(
                        participant.id,
                        start_timing_point.id,
                        dt_timestamp,
                        TimingSource.LLRP
                    )
                    print(f"✓ {participant.full_name} - Start (Chip Start) - {dt_timestamp.strftime('%H:%M:%S')}")
                    return
        
        # Get the next expected timing point for this participant
        timing_point = self._get_next_timing_point(participant.id)
        
        if not timing_point:
            # print(f"No timing point available for {participant.full_name}")
            return
            
        # Check station assignment
        if timing_point.llrp_station_id is not None:
            if station_id is None:
                # No station info, but point expects a station – log and still record
                print(f"⚠️ Expected station {timing_point.llrp_station_id} for '{timing_point.name}' but got no station. Recording anyway.")
            elif timing_point.llrp_station_id != station_id:
                # Wrong station – log warning but still record the time
                print(f"⚠️ Expected station {timing_point.llrp_station_id} for '{timing_point.name}' but got {station_id}. Recording anyway.")
            # If station matches or we chose to record despite mismatch, continue
        
        # Record the time
        # timestamp is a float (epoch time) or datetime object?
        # The service passes float timestamp. record_time expects datetime.
        if isinstance(timestamp, (int, float)):
            dt_timestamp = datetime.fromtimestamp(timestamp)
        else:
            dt_timestamp = timestamp
            
        self.record_time(
            participant.id,
            timing_point.id,
            dt_timestamp,
            TimingSource.LLRP
        )
        
        print(f"✓ {participant.full_name} - {timing_point.name} - {dt_timestamp.strftime('%H:%M:%S')}")
    
    def _get_next_timing_point(self, participant_id):
        """Get the next expected timing point for a participant"""
        session = get_session()
        
        # Get all timing points for this race, ordered
        timing_points = session.query(TimeRecord.timing_point_id).filter(
            and_(
                TimeRecord.race_id == self.race_id,
                TimeRecord.participant_id == participant_id
            )
        ).all()
        
        recorded_point_ids = [tp[0] for tp in timing_points]
        
        # Get all race timing points
        # We need to query them fresh
        all_points = session.query(TimingPoint).filter(
            TimingPoint.race_id == self.race_id
        ).order_by(TimingPoint.order).all()
        
        # Find first unrecorded point
        for point in all_points:
            if point.id not in recorded_point_ids:
                return point
        
        return None  # All points recorded
    
    def record_time(self, participant_id, timing_point_id, timestamp, source=TimingSource.MANUAL, notes=None):
        """Record a time for a participant at a timing point"""
        session = get_session()
        
        time_record = TimeRecord(
            race_id=self.race_id,
            participant_id=participant_id,
            timing_point_id=timing_point_id,
            timestamp=timestamp,
            source=source,
            notes=notes
        )
        
        session.add(time_record)
        session.commit()
        
        # Update race result
        self._update_result(participant_id)
        
        return time_record
    
    def record_manual_time(self, bib_number, timing_point_name, timestamp=None, notes=None):
        """Manually record a time by bib number"""
        if timestamp is None:
            timestamp = datetime.now()
        
        participant_manager = ParticipantManager()
        # Find participant by bib number
        participant = participant_manager.get_participant_by_bib(self.race_id, bib_number)
        if not participant:
            print(f"Participant with bib {bib_number} not found")
            return None
        
        session = get_session()
        # Find timing point by name
        timing_point = session.query(TimingPoint).filter(
            and_(
                TimingPoint.race_id == self.race_id,
                TimingPoint.name == timing_point_name # Case sensitive? Original was iterating and lower()
            )
        ).all()
        
        # Match case-insensitive
        target_tp = None
        for tp in timing_point:
            if tp.name.lower() == timing_point_name.lower():
                target_tp = tp
                break
        
        # If not found by exact query, try fetching all and filtering
        if not target_tp:
             all_tps = session.query(TimingPoint).filter(TimingPoint.race_id == self.race_id).all()
             for tp in all_tps:
                 if tp.name.lower() == timing_point_name.lower():
                     target_tp = tp
                     break
        
        if not target_tp:
            print(f"Timing point '{timing_point_name}' not found")
            return None
        
        return self.record_time(
            participant.id,
            target_tp.id,
            timestamp,
            TimingSource.MANUAL,
            notes
        )
    
    def record_manual_time_auto(self, bib_number, timestamp=None, notes=None):
        """
        Automatically record time at the next expected timing point for a participant.
        This is the simplified workflow - just provide bib number, system determines timing point.
        
        Args:
            bib_number: Participant's bib number
            timestamp: Optional timestamp (defaults to now)
            notes: Optional notes
            
        Returns:
            dict with success status, timing point name, and message
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        participant_manager = ParticipantManager()
        # Find participant by bib number
        participant = participant_manager.get_participant_by_bib(self.race_id, bib_number)
        if not participant:
            return {
                'success': False,
                'error': f"Participant with bib {bib_number} not found in this race"
            }
        
        # Get the next expected timing point for this participant
        timing_point = self._get_next_timing_point(participant.id)
        
        if not timing_point:
            return {
                'success': False,
                'error': f"No more timing points available for bib {bib_number} (all checkpoints recorded)"
            }
        
        # Record the time
        time_record = self.record_time(
            participant.id,
            timing_point.id,
            timestamp,
            TimingSource.MANUAL,
            notes
        )
        
        if time_record:
            return {
                'success': True,
                'timing_point': timing_point.name,
                'participant_name': participant.full_name,
                'timestamp': timestamp.isoformat(),
                'message': f"Bib #{bib_number} recorded at {timing_point.name}"
            }
        else:
            return {
                'success': False,
                'error': f"Failed to record time for bib {bib_number}"
            }
    
    def calculate_results(self):
        """Recalculate results for all participants"""
        session = get_session()
        
        # Get all participants in the race
        participants = session.query(race_participants).filter(
            race_participants.c.race_id == self.race_id
        ).all()
        
        for p in participants:
            self._update_result(p.participant_id, calculate_rankings=False)
            
        # Calculate rankings once at the end
        self._calculate_rankings()

    def _update_result(self, participant_id, calculate_rankings=True):
        """Update or create race result for a participant"""
        session = get_session()
        
        # Get or create result
        result = session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                RaceResult.participant_id == participant_id
            )
        ).first()
        
        if not result:
            # Get bib and category from registration
            reg = session.query(race_participants).filter(
                and_(
                    race_participants.c.race_id == self.race_id,
                    race_participants.c.participant_id == participant_id
                )
            ).first()
            
            # Calculate category
            race = session.query(Race).get(self.race_id)
            # We need the participant object
            participant = session.query(Participant).get(participant_id)
            category = self._calculate_category(participant, race)
            
            result = RaceResult(
                race_id=self.race_id,
                participant_id=participant_id,
                bib_number=reg.bib_number if reg else None,
                category=category,
                status=ParticipantStatus.REGISTERED
            )
            session.add(result)
        
        # Get all time records for this participant
        times = session.query(TimeRecord).filter(
            and_(
                TimeRecord.race_id == self.race_id,
                TimeRecord.participant_id == participant_id
            )
        ).order_by(TimeRecord.timestamp).all()
        
        # Find start and finish times
        start_time = None
        finish_time = None
        split_times = {}
        status = ParticipantStatus.REGISTERED
        
        # Check for Gun Start (Race Start Time)
        race = session.query(Race).get(self.race_id)
        if race.start_time:
            start_time = race.start_time
            status = ParticipantStatus.STARTED
        
        if times:
            for time_record in times:
                # We need to access timing_point relationship. 
                # Since time_record is attached to session, this should work.
                tp = time_record.timing_point
                
                # Use the FIRST read for each timing point (since times are ordered by timestamp)
                if tp.name not in split_times:
                    split_times[tp.name] = time_record.timestamp.isoformat()
                    
                    if tp.is_start:
                        # Chip start overrides gun start
                        start_time = time_record.timestamp
                        status = ParticipantStatus.STARTED
                    elif tp.is_finish:
                        finish_time = time_record.timestamp
                        status = ParticipantStatus.FINISHED
        
        # Don't overwrite DNF/DNS status unless they finished
        if result.status in [ParticipantStatus.DNF, ParticipantStatus.DNS]:
            if status == ParticipantStatus.FINISHED:
                # If they finished, they can't be DNF/DNS
                pass 
            else:
                # Keep existing DNF/DNS status
                status = result.status
        
        # Update result fields
        result.status = status
        result.start_time = start_time
        result.finish_time = finish_time
        result.split_times = json.dumps(split_times)
        result.total_time = None
        
        # Calculate total time
        if start_time and finish_time:
            result.total_time = (finish_time - start_time).total_seconds()
        
        session.commit()
        
        # Recalculate rankings if requested
        if calculate_rankings:
            self._calculate_rankings()
            
    def _calculate_category(self, participant, race):
        """Calculate age group category for participant"""
        if not participant or not participant.age:
            return "Open"
            
        if not race.age_groups:
            return "Open"
            
        try:
            age_groups = json.loads(race.age_groups)
            for group in age_groups:
                # Check gender if specified in group (future proofing)
                # if 'gender' in group and group['gender'] != 'All' ...
                
                if group['min'] <= participant.age <= group['max']:
                    return group['name']
        except:
            pass
            
        return "Open"
    
    def _apply_aging_down(self, finished_results, race):
        """
        Apply aging down logic: if an older participant is faster than the winner
        of a younger age group, they win the younger group and are removed from their own.
        """
        try:
            age_groups = json.loads(race.age_groups)
            # Sort age groups by min age (youngest first)
            age_groups_sorted = sorted(age_groups, key=lambda g: g['min'])
            
            # Build a map of category name to age group definition
            category_to_group = {g['name']: g for g in age_groups_sorted}
            
            # Iteratively apply aging down until stable
            max_iterations = 10  # Prevent infinite loops
            for iteration in range(max_iterations):
                changed = False
                
                # For each age group (youngest to oldest)
                for i, young_group in enumerate(age_groups_sorted):
                    young_category = young_group['name']
                    
                    # Find the current winner of this category
                    young_results = [r for r in finished_results if r.category == young_category]
                    if not young_results:
                        continue
                    
                    # Sort by time to find winner
                    young_results.sort(key=lambda r: r.total_time if r.total_time else float('inf'))
                    current_winner = young_results[0]
                    current_winner_time = current_winner.total_time
                    
                    if not current_winner_time:
                        continue
                    
                    # Check all older age groups for faster participants
                    for older_group in age_groups_sorted[i+1:]:
                        older_category = older_group['name']
                        older_results = [r for r in finished_results if r.category == older_category]
                        
                        for older_result in older_results:
                            if older_result.total_time and older_result.total_time < current_winner_time:
                                # This older participant is faster! Move them down.
                                print(f"Aging down: {older_result.participant.full_name} ({older_category}) -> {young_category} (beat {current_winner_time}s with {older_result.total_time}s)")
                                older_result.category = young_category
                                changed = True
                                # Only move the fastest one per iteration
                                break
                        
                        if changed:
                            break
                    
                    if changed:
                        break
                
                if not changed:
                    # No more changes, we're stable
                    break
                    
        except Exception as e:
            print(f"Error in aging down logic: {e}")
            # Don't crash the ranking calculation if aging down fails
            pass
    
    def _calculate_rankings(self):
        """Calculate rankings for all participants (finished and active)"""
        session = get_session()
        
        # Refresh race object to get latest age groups
        race = session.query(Race).get(self.race_id)
        
        # 1. Get all results that are FINISHED or STARTED
        results = session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                RaceResult.status.in_([ParticipantStatus.FINISHED, ParticipantStatus.STARTED])
            )
        ).all()
        
        # Update categories before ranking
        # This ensures that if age groups changed, everyone is re-categorized
        for result in results:
            # We need the participant object
            if result.participant:
                new_category = self._calculate_category(result.participant, race)
                if new_category != "Open": # Only override if we found a specific group
                     result.category = new_category
                elif result.category == "Open":
                     # If currently Open and we didn't find a group, keep Open.
                     # But if they were in a group that was deleted, they should go back to Open?
                     # For now, let's trust _calculate_category returns "Open" if no match.
                     result.category = new_category
        
        # Apply aging down logic for FINISHED participants only
        finished_results = [r for r in results if r.status == ParticipantStatus.FINISHED]
        if finished_results and race.age_groups:
            self._apply_aging_down(finished_results, race)
        
        # Separate into finished and started
        finished_results = [r for r in results if r.status == ParticipantStatus.FINISHED]
        started_results = [r for r in results if r.status == ParticipantStatus.STARTED]
        
        # Sort finished results by total time
        finished_results.sort(key=lambda r: r.total_time if r.total_time is not None else float('inf'))
        
        # Sort started results by progress
        # We need to find the furthest timing point for each started participant
        if started_results:
            started_ids = [r.participant_id for r in started_results]
            
            # Query to find the latest timing point order and timestamp for each started participant
            # Join TimeRecord with TimingPoint to get the order
            latest_records = session.query(
                TimeRecord.participant_id,
                TimingPoint.order,
                TimeRecord.timestamp
            ).join(
                TimingPoint, TimeRecord.timing_point_id == TimingPoint.id
            ).filter(
                and_(
                    TimeRecord.race_id == self.race_id,
                    TimeRecord.participant_id.in_(started_ids)
                )
            ).order_by(
                TimeRecord.participant_id,
                TimingPoint.order.desc() # Get highest order first
            ).all()
            
            # Map participant_id to (max_order, timestamp)
            progress_map = {}
            for pid, order, timestamp in latest_records:
                if pid not in progress_map:
                    progress_map[pid] = (order, timestamp)
            
            # Sort started results:
            # 1. Higher order is better (descending)
            # 2. Lower timestamp is better (ascending)
            def get_progress_sort_key(result):
                progress = progress_map.get(result.participant_id, (-1, datetime.max))
                return (-progress[0], progress[1])
            
            started_results.sort(key=get_progress_sort_key)
        
        # Combine lists: Finished first, then Started
        ranked_results = finished_results + started_results
        
        # Assign Overall Rank
        for rank, result in enumerate(ranked_results, 1):
            result.overall_rank = rank
            
        # Assign Category Rank
        categories = {}
        for result in ranked_results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
            
        for category, cat_results in categories.items():
            for rank, result in enumerate(cat_results, 1):
                result.category_rank = rank
                
        # Assign Gender Rank
        genders = {}
        for result in ranked_results:
            participant = result.participant
            if participant and participant.gender:
                if participant.gender not in genders:
                    genders[participant.gender] = []
                genders[participant.gender].append(result)
                
        for gender, gender_results in genders.items():
            for rank, result in enumerate(gender_results, 1):
                result.gender_rank = rank
        
        # Clear ranks for non-ranked participants (Registered, DNF, DNS)
        non_ranked = session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                ~RaceResult.status.in_([ParticipantStatus.FINISHED, ParticipantStatus.STARTED])
            )
        ).all()
        
        for result in non_ranked:
            result.overall_rank = None
            result.category_rank = None
            result.gender_rank = None
            
        session.commit()
    
    def get_live_results(self, limit=None):
        """Get current race standings"""
        session = get_session()
        
        query = session.query(RaceResult).filter(
            RaceResult.race_id == self.race_id
        ).order_by(
            RaceResult.status.desc(),
            RaceResult.total_time
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def mark_dnf(self, participant_id, notes=None):
        """Mark a participant as Did Not Finish"""
        session = get_session()
        
        result = session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                RaceResult.participant_id == participant_id
            )
        ).first()
        
        if result:
            result.status = ParticipantStatus.DNF
            result.notes = notes
            session.commit()
            self._calculate_rankings()
    
    def mark_dns(self, participant_id, notes=None):
        """Mark a participant as Did Not Start"""
        session = get_session()
        
        result = session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                RaceResult.participant_id == participant_id
            )
        ).first()
        
        if result:
            result.status = ParticipantStatus.DNS
            result.notes = notes
            session.commit()
            self._calculate_rankings()
