import sys
sys.path.insert(0, r'.')

# Patch TTS_ENABLED before any main imports
import config_loader
config_loader.TTS_ENABLED = False

# Now import and run
from main import _text_mode_async
import asyncio

print('Running JARVIS text mode (TTS disabled)...')
print('Type quit or exit to stop\n')

async def run_text_mode():
    try:
        await _text_mode_async()
    except KeyboardInterrupt:
        print('\n[JARVIS] Bye!')
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(run_text_mode())