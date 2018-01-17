import os
import pandas as pd

CSV_FILE = 'walgreens_metadata.csv'

def check_image():
    df = pd.read_csv(CSV_FILE, sep='\t')
    cnt = 0
    missing = 0
    for path in df['S3 Path']:
        if not os.path.exists(path):
            missing += 1
            print(path)
        cnt += 1
    print('total: {}, miss: {}'.format(cnt, missing))


if __name__ == '__main__':
    check_image()