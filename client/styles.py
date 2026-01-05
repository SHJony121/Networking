"""
Centralized styles for the application
"""

class Theme:
    # Modern Dark Theme Colors
    BACKGROUND = "#121212"       # Very dark grey, almost black
    SURFACE = "#1E1E1E"          # Slightly lighter for cards/containers
    SURFACE_HOVER = "#2D2D2D"    # Hover state for surface
    
    PRIMARY = "#BB86FC"          # Purple - Primary accent
    PRIMARY_VARIANT = "#3700B3"  # Darker purple
    SECONDARY = "#03DAC6"        # Teal - Secondary accent
    
    ERROR = "#CF6679"            # Pinkish red for errors
    SUCCESS = "#00E676"          # Bright green
    
    TEXT_HIGH = "#FFFFFF"        # High emphasis text
    TEXT_MED = "#B0B0B0"         # Medium emphasis text
    TEXT_DISABLED = "#6E6E6E"    # Disabled text
    
    DIVIDER = "#2C2C2C"          # Divider lines

    # Reusable Stylesheets
    
    # 1. Main Window
    MAIN_WINDOW = f"""
        QWidget {{
            background-color: {BACKGROUND};
            color: {TEXT_HIGH};
            font-family: 'Segoe UI', 'Roboto', sans-serif;
        }}
    """
    
    # 2. Cards (Container widgets)
    CARD = f"""
        QWidget {{
            background-color: {SURFACE};
            border-radius: 12px;
            border: 1px solid {DIVIDER};
        }}
    """
    
    # 3. Inputs
    INPUT = f"""
        QLineEdit {{
            background-color: #2C2C2C;
            border: 1px solid #3E3E3E;
            border-radius: 12px;
            padding: 18px;
            color: {TEXT_HIGH};
            font-size: 18px;
        }}
        QLineEdit:focus {{
            border: 1px solid {PRIMARY};
            background-color: #333333;
        }}
    """
    
    # 4. Buttons
    BTN_PRIMARY = f"""
        QPushButton {{
            background-color: {PRIMARY};
            color: #000000;
            border-radius: 30px;
            font-weight: bold;
            font-size: 20px;
            padding: 16px 32px;
        }}
        QPushButton:hover {{
            background-color: #A370F7;
        }}
        QPushButton:pressed {{
            background-color: {PRIMARY_VARIANT};
        }}
    """
    
    BTN_SECONDARY = f"""
        QPushButton {{
            background-color: transparent;
            border: 2px solid {PRIMARY};
            color: {PRIMARY};
            border-radius: 30px;
            font-weight: bold;
            font-size: 18px;
            padding: 12px 24px;
        }}
        QPushButton:hover {{
            background-color: rgba(187, 134, 252, 0.1);
        }}
    """
    
    BTN_DANGER = f"""
        QPushButton {{
            background-color: {ERROR};
            color: white;
            border-radius: 30px;
            font-weight: bold;
            font-size: 16px;
            padding: 12px 24px;
        }}
        QPushButton:hover {{
            background-color: #B05566;
        }}
    """
    
    # Square toggle buttons (Mic/Cam in home)
    BTN_TOGGLE = f"""
        QPushButton {{
            background-color: #2C2C2C;
            color: {TEXT_MED};
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #3E3E3E;
            font-weight: bold;
            font-size: 16px;
        }}
        QPushButton:checked {{
            background-color: {SECONDARY};
            color: black;
            border: 1px solid {SECONDARY};
        }}
        QPushButton:hover {{
            border: 1px solid {TEXT_MED};
        }}
    """

    # Floating Control Bar Buttons (Circular)
    BTN_CONTROL = f"""
        QPushButton {{
            background-color: #2C2C2C;
            border-radius: 35px; 
            border: none;
            padding: 20px;
        }}
        QPushButton:hover {{
            background-color: #3E3E3E;
        }}
        QPushButton:checked {{
            background-color: {TEXT_HIGH}; 
        }}
    """
    
    TAB_WIDGET = f"""
        QTabWidget::pane {{
            border: 1px solid {DIVIDER};
            border-radius: 8px;
            background-color: {SURFACE};
        }}
        QTabBar::tab {{
            background-color: {BACKGROUND};
            color: {TEXT_MED};
            padding: 10px 20px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {SURFACE};
            color: {PRIMARY};
            border-bottom: 2px solid {PRIMARY};
        }}
    """
