"""
Race Report Generation
"""
from datetime import datetime
from models import RaceResult, ParticipantStatus
from database import get_session
from race_manager import RaceManager
from tabulate import tabulate
import json
import csv
from sqlalchemy import and_


class ReportGenerator:
    """Generates race reports in various formats"""
    
    def __init__(self, race_id):
        self.race_id = race_id
        self.session = get_session()
        self.race_manager = RaceManager()
        self.race = self.race_manager.get_race(race_id)
        
        if not self.race:
            raise ValueError(f"Race {race_id} not found")
    
    def generate_text_report(self):
        """Generate a text-based race report"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"RACE REPORT: {self.race.name}")
        lines.append(f"Date: {self.race.date.strftime('%Y-%m-%d')}")
        lines.append(f"Type: {self.race.race_type.value.title()}")
        if self.race.location:
            lines.append(f"Location: {self.race.location}")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall Results
        lines.append("OVERALL RESULTS")
        lines.append("-" * 80)
        results = self._get_finished_results()
        
        if results:
            table_data = []
            for result in results:
                participant = result.participant
                time_str = self._format_time(result.total_time) if result.total_time else "N/A"
                table_data.append([
                    result.overall_rank or "-",
                    result.bib_number or "-",
                    participant.full_name,
                    participant.gender or "-",
                    result.category or "-",
                    time_str
                ])
            
            lines.append(tabulate(
                table_data,
                headers=["Rank", "Bib", "Name", "Gender", "Category", "Time"],
                tablefmt="simple"
            ))
        else:
            lines.append("No finishers yet.")
        
        lines.append("")
        
        # Category Results
        categories = self._get_results_by_category()
        if categories:
            lines.append("RESULTS BY CATEGORY")
            lines.append("-" * 80)
            
            for category, cat_results in categories.items():
                lines.append(f"\n{category}")
                table_data = []
                for result in cat_results:
                    participant = result.participant
                    time_str = self._format_time(result.total_time) if result.total_time else "N/A"
                    table_data.append([
                        result.category_rank or "-",
                        result.bib_number or "-",
                        participant.full_name,
                        time_str
                    ])
                
                lines.append(tabulate(
                    table_data,
                    headers=["Rank", "Bib", "Name", "Time"],
                    tablefmt="simple"
                ))
        
        lines.append("")
        
        # DNF/DNS
        dnf_dns = self._get_dnf_dns()
        if dnf_dns:
            lines.append("DID NOT FINISH / DID NOT START")
            lines.append("-" * 80)
            table_data = []
            for result in dnf_dns:
                participant = result.participant
                table_data.append([
                    result.bib_number or "-",
                    participant.full_name,
                    result.status.value.upper(),
                    result.notes or ""
                ])
            
            lines.append(tabulate(
                table_data,
                headers=["Bib", "Name", "Status", "Notes"],
                tablefmt="simple"
            ))
        
        lines.append("")
        lines.append("=" * 80)
        lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def generate_csv_report(self, filename):
        """Generate a CSV report"""
        results = self._get_finished_results()
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Overall Rank', 'Category Rank', 'Gender Rank',
                'Bib', 'First Name', 'Last Name', 'Gender', 'Age',
                'Category', 'Total Time (seconds)', 'Total Time',
                'Status', 'Split Times'
            ])
            
            for result in results:
                participant = result.participant
                time_str = self._format_time(result.total_time) if result.total_time else ""
                
                writer.writerow([
                    result.overall_rank or "",
                    result.category_rank or "",
                    result.gender_rank or "",
                    result.bib_number or "",
                    participant.first_name,
                    participant.last_name,
                    participant.gender or "",
                    participant.age or "",
                    result.category or "",
                    result.total_time or "",
                    time_str,
                    result.status.value,
                    result.split_times or ""
                ])
        
        print(f"CSV report saved to: {filename}")
    
    def generate_html_report(self, filename):
        """Generate an HTML report"""
        results = self._get_finished_results()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.race.name} - Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .header {{ background-color: #f8f8f8; padding: 20px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.race.name}</h1>
        <p><strong>Date:</strong> {self.race.date.strftime('%Y-%m-%d')}</p>
        <p><strong>Type:</strong> {self.race.race_type.value.title()}</p>
        {f'<p><strong>Location:</strong> {self.race.location}</p>' if self.race.location else ''}
    </div>
    
    <h2>Overall Results</h2>
    <table>
        <tr>
            <th>Rank</th>
            <th>Bib</th>
            <th>Name</th>
            <th>Gender</th>
            <th>Category</th>
            <th>Time</th>
        </tr>
"""
        
        for result in results:
            participant = result.participant
            time_str = self._format_time(result.total_time) if result.total_time else "N/A"
            html += f"""        <tr>
            <td>{result.overall_rank or '-'}</td>
            <td>{result.bib_number or '-'}</td>
            <td>{participant.full_name}</td>
            <td>{participant.gender or '-'}</td>
            <td>{result.category or '-'}</td>
            <td>{time_str}</td>
        </tr>
"""
        
        html += """    </table>
    
    <p style="margin-top: 40px; color: #666;">
        Report generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
    </p>
</body>
</html>"""
        
        with open(filename, 'w') as f:
            f.write(html)
        
        print(f"HTML report saved to: {filename}")
    
    def _get_finished_results(self):
        """Get all finished results, ordered by rank"""
        return self.session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                RaceResult.status == ParticipantStatus.FINISHED
            )
        ).order_by(RaceResult.overall_rank).all()
    
    def _get_results_by_category(self):
        """Get results grouped by category"""
        results = self._get_finished_results()
        categories = {}
        
        for result in results:
            category = result.category or "Open"
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        return categories
    
    def _get_dnf_dns(self):
        """Get DNF and DNS participants"""
        return self.session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == self.race_id,
                RaceResult.status.in_([ParticipantStatus.DNF, ParticipantStatus.DNS])
            )
        ).all()
    
    def _format_time(self, seconds):
        """Format seconds as HH:MM:SS"""
        if seconds is None:
            return "N/A"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
