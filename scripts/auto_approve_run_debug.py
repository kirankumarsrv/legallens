import builtins
import runpy
import sys
import os

# Ensure project root is on sys.path so package imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

"""
Auto-approve runner for workflows.lawyer_agent.run_debug

This script temporarily patches `input()` to always return 'approve',
runs the debug runner module, and restores `input()` afterwards.

Run: python scripts/auto_approve_run_debug.py
"""

def main():
    orig_input = builtins.input
    try:
        builtins.input = lambda prompt='': 'approve'
        runpy.run_module('workflows.lawyer_agent.run_debug', run_name='__main__')
    finally:
        builtins.input = orig_input


if __name__ == '__main__':
    main()
