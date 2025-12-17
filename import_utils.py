"""
Participant Import Utilities
Handle importing participants from Excel files
"""
import pandas as pd
from datetime import datetime
from models import Participant, Race, race_participants
from database import get_session


def map_headers(columns):
    """
    Map various possible header names to standardized field names
    Returns a dictionary mapping standardized names to actual column names
    """
    # Define all possible variations for each field
    header_mappings = {
        'first_name': ['first_name', 'firstname', 'first', 'forename', 'given_name', 'name'],
        'last_name': ['last_name', 'lastname', 'last', 'surname', 'family_name'],
        'email': ['email', 'email_address', 'e-mail', 'mail'],
        'phone': ['phone', 'telephone', 'mobile', 'cell', 'contact', 'phone_number'],
        'gender': ['gender', 'sex', 'm/f'],
        'age': ['age', 'years', 'yrs'],
        'date_of_birth': ['date_of_birth', 'dob', 'birth_date', 'birthdate', 'birthday', 'born'],
        'rfid_tag': ['rfid_tag', 'rfid', 'tag', 'chip', 'chip_number', 'epc'],
        'bib_number': ['bib_number', 'bib', 'number', 'race_number', 'bib_no', 'no'],
        'category': ['category', 'age_group', 'agegroup', 'division', 'class']
    }
    
    # Normalize column names (lowercase, remove spaces and special chars)
    normalized_cols = {}
    for col in columns:
        normalized = str(col).lower().strip().replace(' ', '_').replace('-', '_').replace('.', '')
        normalized_cols[normalized] = col
    
    # Find matches
    field_map = {}
    for field, variations in header_mappings.items():
        for variation in variations:
            if variation in normalized_cols:
                field_map[field] = normalized_cols[variation]
                break
    
    return field_map


def get_next_bib_number(session, race_id):
    """Get the next available bib number for a race"""
    from sqlalchemy import func
    
    # Get highest bib number currently assigned
    result = session.query(func.max(race_participants.c.bib_number)).filter(
        race_participants.c.race_id == race_id
    ).scalar()
    
    if result:
        try:
            # Try to convert to int and increment
            return str(int(result) + 1)
        except:
            # If not numeric, start from 1
            return "1"
    return "1"



def normalize_gender(value):
    """
    Normalize gender input to 'M' or 'F'
    Handles: M, Male, MALE, Open (maps to M?), Female, F, etc.
    """
    if not value:
        return None
        
    val = str(value).strip().upper()
    
    if val in ['M', 'MALE', 'MAN', 'BOY', 'OPEN']: # User requested Open -> Male/Female. Assuming Open often implies Male/Open category? 
        # Wait, "Open" is ambiguous. But user said "values of M, Male, MALE and Open... need to calculated to Male or Female".
        # If I map Open to M, it might be wrong for a female in Open category.
        # But usually "Open" category is effectively the Male category in many races (Men/Open vs Women).
        # Let's map Open to M for now based on the grouping in the prompt "M, Male, MALE and Open".
        return 'M'
    
    if val in ['F', 'FEMALE', 'WOMAN', 'GIRL', 'W']:
        return 'F'
        
    return val # Return original if not matched (e.g. 'X')

def import_participants_from_excel(file_path, race_id=None):
    """
    Import participants from an Excel file
    
    Automatically maps various header formats to expected fields.
    If race_id is provided and bib numbers are in the file, participants are registered.
    If race_id is provided but no bib numbers, bibs are auto-assigned.
    """
    session = get_session()
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Map headers to standardized field names
        field_map = map_headers(df.columns)
        
        # Rename columns based on mapping
        rename_dict = {v: k for k, v in field_map.items()}
        df.rename(columns=rename_dict, inplace=True)
        
        imported_count = 0
        updated_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Extract participant data - handle both string and numeric values
                first_name = str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else ''
                last_name = str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else ''
                email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None
                
                # Normalize gender
                raw_gender = row.get('gender')
                gender = normalize_gender(raw_gender) if pd.notna(raw_gender) else None
                
                rfid_tag = str(row.get('rfid_tag', '')).strip() if pd.notna(row.get('rfid_tag')) else None
                
                # Handle age
                age = None
                if pd.notna(row.get('age')):
                    try:
                        age = int(row.get('age'))
                    except:
                        pass
                
                # Parse date of birth to calculate age if age not provided
                if not age and pd.notna(row.get('date_of_birth')):
                    dob_value = row.get('date_of_birth')
                    dob = None
                    if isinstance(dob_value, str):
                        try:
                            dob = datetime.strptime(dob_value, '%Y-%m-%d').date()
                        except:
                            try:
                                dob = datetime.strptime(dob_value, '%d/%m/%Y').date()
                            except:
                                pass
                    elif isinstance(dob_value, datetime):
                        dob = dob_value.date()
                    
                    # Calculate age from date of birth
                    # British Triathlon rules: age as of December 31st of the current year
                    if dob:
                        current_year = datetime.now().year
                        dec_31_this_year = datetime(current_year, 12, 31).date()
                        age = dec_31_this_year.year - dob.year - ((dec_31_this_year.month, dec_31_this_year.day) < (dob.month, dob.day))
                
                if not first_name or not last_name:
                    errors.append(f"Row {index + 2}: Missing first or last name")
                    continue
                
                # Check if participant exists (by email or RFID tag)
                participant = None
                if email and email.strip():
                    participant = session.query(Participant).filter_by(email=email).first()
                if not participant and rfid_tag and rfid_tag.strip():
                    participant = session.query(Participant).filter_by(rfid_tag=rfid_tag).first()
                
                if participant:
                    # Update existing participant
                    participant.first_name = first_name
                    participant.last_name = last_name
                    if gender:
                        participant.gender = gender
                    if age:
                        participant.age = age
                    if dob:
                        participant.date_of_birth = dob
                    if rfid_tag:
                        participant.rfid_tag = rfid_tag
                    updated_count += 1
                else:
                    # Create new participant
                    participant = Participant(
                        first_name=first_name,
                        last_name=last_name,
                        email=email if email and email.strip() else None,
                        gender=gender,
                        age=age,
                        date_of_birth=dob,  # Store date of birth if available
                        rfid_tag=rfid_tag if rfid_tag and rfid_tag.strip() else None
                    )
                    session.add(participant)
                    session.flush()  # Get participant.id
                    imported_count += 1
                
                # Handle race registration if race_id is provided
                if race_id:
                    # Check if already registered
                    existing_reg = session.query(race_participants).filter_by(
                        race_id=race_id,
                        participant_id=participant.id
                    ).first()
                    
                    if not existing_reg:
                        # Get bib number - use from file or auto-assign
                        bib_number = None
                        if pd.notna(row.get('bib_number')):
                            bib_number = str(row.get('bib_number')).strip()
                        else:
                            # Auto-assign next available bib number
                            bib_number = get_next_bib_number(session, race_id)
                        
                        category = str(row.get('category', 'Open')).strip() if pd.notna(row.get('category')) else 'Open'
                        
                        # Register participant for race
                        session.execute(
                            race_participants.insert().values(
                                race_id=race_id,
                                participant_id=participant.id,
                                bib_number=bib_number,
                                category=category
                            )
                        )
            
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        
        session.commit()
        
        return {
            'success': True,
            'imported': imported_count,
            'updated': updated_count,
            'errors': errors,
            'total_rows': len(df)
        }
    
    except Exception as e:
        session.rollback()
        return {
            'success': False,
            'error': str(e),
            'imported': 0,
            'updated': 0,
            'errors': []
        }
