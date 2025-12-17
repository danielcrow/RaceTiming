"""
Race Templates
Pre-configured race templates for common race types
"""

RACE_TEMPLATES = {
    "sprint_duathlon": {
        "name": "Sprint Duathlon",
        "race_type": "duathlon",
        "description": "5K Run - 20K Bike - 2.5K Run",
        "age_groups": ["Juniors (U20)", "Seniors (20-39)", "Vets (40-49)", "Super Vets (50-59)", "Over 60s (60-69)", "Over 70s (70+)"],
        "legs": [
            {
                "name": "Run 1",
                "leg_type": "run",
                "distance": 5.0,
                "distance_unit": "km",
                "order": 1
            },
            {
                "name": "Bike",
                "leg_type": "bike",
                "distance": 20.0,
                "distance_unit": "km",
                "order": 2
            },
            {
                "name": "Run 2",
                "leg_type": "run",
                "distance": 2.5,
                "distance_unit": "km",
                "order": 3
            }
        ],
        "timing_points": [
            {"name": "Start", "order": 1, "is_start": True, "is_finish": False},
            {"name": "T1 - Run to Bike", "order": 2, "is_start": False, "is_finish": False},
            {"name": "T2 - Bike to Run", "order": 3, "is_start": False, "is_finish": False},
            {"name": "Finish", "order": 4, "is_start": False, "is_finish": True}
        ]
    },
    
    "standard_duathlon": {
        "name": "Standard Duathlon",
        "race_type": "duathlon",
        "description": "10K Run - 40K Bike - 5K Run",
        "age_groups": ["Juniors (U20)", "Seniors (20-39)", "Vets (40-49)", "Super Vets (50-59)", "Over 60s (60-69)", "Over 70s (70+)"],
        "legs": [
            {
                "name": "Run 1",
                "leg_type": "run",
                "distance": 10.0,
                "distance_unit": "km",
                "order": 1
            },
            {
                "name": "Bike",
                "leg_type": "bike",
                "distance": 40.0,
                "distance_unit": "km",
                "order": 2
            },
            {
                "name": "Run 2",
                "leg_type": "run",
                "distance": 5.0,
                "distance_unit": "km",
                "order": 3
            }
        ],
        "timing_points": [
            {"name": "Start", "order": 1, "is_start": True, "is_finish": False},
            {"name": "T1 - Run to Bike", "order": 2, "is_start": False, "is_finish": False},
            {"name": "T2 - Bike to Run", "order": 3, "is_start": False, "is_finish": False},
            {"name": "Finish", "order": 4, "is_start": False, "is_finish": True}
        ]
    },
    
    "long_duathlon": {
        "name": "Long Distance Duathlon",
        "race_type": "duathlon",
        "description": "15K Run - 60K Bike - 10K Run",
        "age_groups": ["Juniors (U20)", "Seniors (20-39)", "Vets (40-49)", "Super Vets (50-59)", "Over 60s (60-69)", "Over 70s (70+)"],
        "legs": [
            {
                "name": "Run 1",
                "leg_type": "run",
                "distance": 15.0,
                "distance_unit": "km",
                "order": 1
            },
            {
                "name": "Bike",
                "leg_type": "bike",
                "distance": 60.0,
                "distance_unit": "km",
                "order": 2
            },
            {
                "name": "Run 2",
                "leg_type": "run",
                "distance": 10.0,
                "distance_unit": "km",
                "order": 3
            }
        ],
        "timing_points": [
            {"name": "Start", "order": 1, "is_start": True, "is_finish": False},
            {"name": "T1 - Run to Bike", "order": 2, "is_start": False, "is_finish": False},
            {"name": "T2 - Bike to Run", "order": 3, "is_start": False, "is_finish": False},
            {"name": "Finish", "order": 4, "is_start": False, "is_finish": True}
        ]
    },
    
    "sprint_aquathlon": {
        "name": "Sprint Aquathlon",
        "race_type": "aquathlon",
        "description": "750m Swim - 5K Run",
        "age_groups": ["Juniors (U20)", "Seniors (20-39)", "Vets (40-49)", "Super Vets (50-59)", "Over 60s (60-69)", "Over 70s (70+)"],
        "legs": [
            {
                "name": "Swim",
                "leg_type": "swim",
                "distance": 0.75,
                "distance_unit": "km",
                "order": 1
            },
            {
                "name": "Run",
                "leg_type": "run",
                "distance": 5.0,
                "distance_unit": "km",
                "order": 2
            }
        ],
        "timing_points": [
            {"name": "Start", "order": 1, "is_start": True, "is_finish": False},
            {"name": "T1 - Swim to Run", "order": 2, "is_start": False, "is_finish": False},
            {"name": "Finish", "order": 3, "is_start": False, "is_finish": True}
        ]
    },
    
    "standard_aquathlon": {
        "name": "Standard Aquathlon",
        "race_type": "aquathlon",
        "description": "1.5K Swim - 10K Run",
        "age_groups": ["Juniors (U20)", "Seniors (20-39)", "Vets (40-49)", "Super Vets (50-59)", "Over 60s (60-69)", "Over 70s (70+)"],
        "legs": [
            {
                "name": "Swim",
                "leg_type": "swim",
                "distance": 1.5,
                "distance_unit": "km",
                "order": 1
            },
            {
                "name": "Run",
                "leg_type": "run",
                "distance": 10.0,
                "distance_unit": "km",
                "order": 2
            }
        ],
        "timing_points": [
            {"name": "Start", "order": 1, "is_start": True, "is_finish": False},
            {"name": "T1 - Swim to Run", "order": 2, "is_start": False, "is_finish": False},
            {"name": "Finish", "order": 3, "is_start": False, "is_finish": True}
        ]
    },
    
    "long_aquathlon": {
        "name": "Long Distance Aquathlon",
        "race_type": "aquathlon",
        "description": "2K Swim - 15K Run",
        "age_groups": ["Juniors (U20)", "Seniors (20-39)", "Vets (40-49)", "Super Vets (50-59)", "Over 60s (60-69)", "Over 70s (70+)"],
        "legs": [
            {
                "name": "Swim",
                "leg_type": "swim",
                "distance": 2.0,
                "distance_unit": "km",
                "order": 1
            },
            {
                "name": "Run",
                "leg_type": "run",
                "distance": 15.0,
                "distance_unit": "km",
                "order": 2
            }
        ],
        "timing_points": [
            {"name": "Start", "order": 1, "is_start": True, "is_finish": False},
            {"name": "T1 - Swim to Run", "order": 2, "is_start": False, "is_finish": False},
            {"name": "Finish", "order": 3, "is_start": False, "is_finish": True}
        ]
    }
}


def get_template(template_id):
    """Get a race template by ID"""
    return RACE_TEMPLATES.get(template_id)


def get_all_templates():
    """Get all available race templates"""
    return RACE_TEMPLATES


def get_templates_by_type(race_type):
    """Get all templates for a specific race type"""
    return {k: v for k, v in RACE_TEMPLATES.items() if v['race_type'] == race_type}
