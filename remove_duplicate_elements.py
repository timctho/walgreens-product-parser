import pandas as pd

FILE_NAME = 'walgreens_metadata.csv'


def remove_duplicates(data):
    remove_idx = []

    # sorted by image name
    data = data.sort_values(by=['S3 Path'])

    prev = data['S3 Path'].iloc[0]
    for i in range(1, len(data['S3 Path'])):
        cur = data['S3 Path'].iloc[i]
        if cur == prev:
            remove_idx.append(data['Unnamed: 0'].iloc[i])
        else:
            prev = cur
    df = data.drop(remove_idx, axis=0)
    df = df[['Site', 'Brand', 'Category', 'SKU Description', 'Image URL', 'S3 Path']]
    df.to_csv('walgreens_metadata.csv', sep='\t', encoding='utf-8')


if __name__ == '__main__':
    data = pd.read_csv(FILE_NAME, sep='\t')
    remove_duplicates(data)
