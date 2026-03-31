"""Sound notifications for PokeMMO Companion."""
import sys
import threading


def play_shiny_alert():
    """Play a distinctive beep pattern for shiny detection."""
    if sys.platform != 'win32':
        return

    def _play():
        try:
            import winsound
            # Celebratory pattern: rising tones
            winsound.Beep(800, 150)
            winsound.Beep(1000, 150)
            winsound.Beep(1200, 150)
            winsound.Beep(1500, 300)
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


def play_encounter_beep():
    """Short beep for encounter detection."""
    if sys.platform != 'win32':
        return

    def _play():
        try:
            import winsound
            winsound.Beep(600, 50)
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


def play_notification():
    """Generic notification sound."""
    if sys.platform != 'win32':
        return

    def _play():
        try:
            import winsound
            winsound.Beep(1000, 100)
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


if __name__ == "__main__":
    print("Testing shiny alert...")
    play_shiny_alert()
    import time
    time.sleep(1)
    print("Testing encounter beep...")
    play_encounter_beep()
    time.sleep(0.5)
    print("Testing notification...")
    play_notification()
