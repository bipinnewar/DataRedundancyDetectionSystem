from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import numpy as np
import time
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def edit_distance(s1, s2):
    m = len(s1)
    n = len(s2)

    d = [[0] * (n + 1) for i in range(m + 1)]

    for i in range(1, m + 1):
        d[i][0] = i
    for j in range(1, n + 1):
        d[0][j] = j

    for j in range(1, n + 1):
        for i in range(1, m + 1):
            if s1[i - 1] == s2[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]) + 1

    return d[m][n]

def count_duplicates(records, id_column_name):
    count_dict = {}

    for row in records:
        record = tuple(row[1:])
        if record in count_dict:
            count_dict[record]['count'] += 1
            count_dict[record]['ids'].append(row[0])
        else:
            count_dict[record] = {'count': 1, 'ids': [row[0]]}

    duplicates = []
    total = 0
    for record, details in count_dict.items():
        if details['count'] > 1:
            duplicates.append(f"IDs: {', '.join(str(id) for id in details['ids'])}, {record}: duplicate count: {details['count']}")
            total += details['count']

    return duplicates, total

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            session['file_path'] = file_path
            return redirect(url_for('select_columns'))
    return render_template('upload.html')

@app.route('/select_columns', methods=['GET', 'POST'])
def select_columns():
    if 'file_path' not in session:
        return redirect(url_for('index'))
    
    file_path = session['file_path']
    df = pd.read_csv(file_path, encoding='ISO-8859-1')

    if request.method == 'POST':
        selected_columns = request.form.getlist('columns')
        if selected_columns:
            session['selected_columns'] = selected_columns
            return redirect(url_for('result'))

    return render_template('select_columns.html', columns=df.columns)

@app.route('/result')
def result():
    if 'file_path' not in session or 'selected_columns' not in session:
        return redirect(url_for('index'))
    
    file_path = session['file_path']
    selected_columns = session['selected_columns']
    
    df = pd.read_csv(file_path, encoding='ISO-8859-1')
    id_column_name = df.columns[0]
    df.dropna(subset=selected_columns, inplace=True)
    df['std_att'] = df[selected_columns].astype(str).agg(''.join, axis=1)
    
    std = df[[id_column_name] + selected_columns].values
    unique_ids = []
    unique_std_att = []
    probable_dup = []
    comparison = 0
    threshold = 2
    chunk_size = 50
    std_att = df['std_att']
    
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        std_chunk = std_att.iloc[i:i+chunk_size]
        m = len(chunk)
        for j in range(m):
            for k in range(j + 1, m):
                id_j = str(chunk.iloc[j][id_column_name])
                id_k = str(chunk.iloc[k][id_column_name])
                dist = edit_distance(std_chunk.iloc[j], std_chunk.iloc[k])
                comparison += 1
                if dist <= threshold:
                    if dist > 0:
                        edit = (dist, f"Edit distance between ({id_j}){chunk.iloc[j]['std_att']} and ({id_k}){chunk.iloc[k]['std_att']} : {dist}")
                        probable_dup.append(edit)
                    if id_j not in unique_ids:
                        unique_ids.append(id_j)
                        unique_std_att.append((chunk.iloc[j][id_column_name], chunk.iloc[j]['std_att']))
                    if id_k not in unique_ids:
                        unique_ids.append(id_k)
                        unique_std_att.append((chunk.iloc[k][id_column_name], chunk.iloc[k]['std_att']))

    probable_dup = sorted(probable_dup, key=lambda x: x[0])
    duplicates, total_duplicates = count_duplicates(unique_std_att, id_column_name)

    return render_template('result.html', probable_dup=probable_dup, duplicates=duplicates,
                           total_duplicates=total_duplicates, comparison=comparison,
                           num_records=len(df))

if __name__ == '__main__':
    app.run(debug=True)
