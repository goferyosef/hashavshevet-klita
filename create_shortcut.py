"""
Creates a desktop shortcut for the built executable.
Run after build.bat, or run directly pointing to any .exe.
Requires: pip install pywin32
"""

import os
import sys


def create_shortcut(target_path: str = None):
    try:
        import win32com.client
    except ImportError:
        print("pywin32 not installed — skipping shortcut creation.")
        print("Run:  pip install pywin32")
        return

    if target_path is None:
        target_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "dist", "קליטה_לחשבשבת.exe",
        )

    if not os.path.exists(target_path):
        print(f"Executable not found at {target_path}")
        print("Build the project first with build.bat")
        return

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "קליטה לחשבשבת.lnk")
    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico"
    )

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    if os.path.exists(icon_path):
        shortcut.IconLocation = icon_path
    shortcut.Description = "קליטה לחשבשבת — עיבוד חשבוניות וקבלות"
    shortcut.save()

    print(f"Shortcut created: {shortcut_path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    create_shortcut(target)
