"""Ban/pick, then the match engine. No club career."""
import multiprocessing as mp
from pathlib import Path
import argparse
from app import App

def main():
    mp.freeze_support()
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=1)
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--frames',type=int)
    parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args()
    application=App(args.seed,args.headless,match_only=True)
    try:application.run(args.frames,args.screenshot)
    finally:application.close()

if __name__=='__main__':main()
