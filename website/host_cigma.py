#! /usr/bin/env python

import numpy as np
import pickle
import os
from flask import Flask, render_template, url_for, send_from_directory
from flask_frozen import Freezer

# Global table data variable:
t = None

app = Flask(__name__)
app.config['DOC_FOLDER'] = os.path.join(os.path.dirname(__file__), 'doc/build/html/')
freezer = Freezer(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about/')
def about():
    return render_template('about.html')

@freezer.register_generator
def source():
    for source_id in t.keys():
        yield {'source_id': source_id}

@app.route('/source/<int:source_id>.html')
def source(source_id):
    if source_id not in t.keys():
        return render_template('source_not_found.html', source_id=source_id)
    else:
        data = t[source_id]
        keys = data.keys()
        keys.sort()
        #data['sdss_thumbnail'] = url_for('static', filename='img/' + os.path.basename(data['sdss_thumbnail']))
        data['sdss_thumbnail'] = os.path.basename(data['sdss_thumbnail'])
        data['shortsum_png'] = os.path.basename(data['shortsum_png'])
        
        current = np.where(np.array(t.keys()) == source_id)[0][0]
        if current == t.keys()[0]:
            prev = None
        else:
            prev = str(t.keys()[current - 1])
        
        if current == t.keys()[len(t) - 1]:
            next = None
        else:
            next = str(t.keys()[current + 1])
        nav = {'keys':keys, 'prev':prev, 'next':next, 'first':t.keys()[0], 'last':t.keys()[-1]}
        
        return render_template('source.html', source_id=source_id, data=data, nav=nav)

def load_data(pickle_file):
    global t
    with open(pickle_file, 'r') as f:
        t = pickle.load(f)
    t = t.to_dict(orient='index')

@freezer.register_generator
def doc():
    all_files = []
    for root, dirs, files in os.walk(app.config['DOC_FOLDER']):
        root = root[len(app.config['DOC_FOLDER']):]
        for name in files:
            if name[0] != '.':
                all_files.append({'filename': os.path.join(root, name)})
    return all_files

@app.route('/doc/')
@app.route('/doc/<path:filename>')
def doc(filename='index.html'):
    return send_from_directory(app.config['DOC_FOLDER'], filename)

def host_cigma(pickle_file='./cigma_data.pkl', static=False):
    '''
    Read in pickle file and host the CIGMA website.
    '''
    # Read in data:
    load_data(pickle_file)
    
    if static:
        # Generate static html files:
        freezer.freeze()
        print('To host static files:')
        print('  cd {:s} ; open http://0.0.0.0:8000 ; python3 -m http.server\n'.format( \
            os.path.relpath(os.path.join(os.path.dirname(__file__), app.config['FREEZER_DESTINATION']))))
    else:
        # Launch flask server:
        app.run(debug=True)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Host the CIGMA website.')
    parser.add_argument('-p', dest='pickle_file', type=str, 
        help='Pickle file containing data.', 
        default='./cigma_data.pkl')
    parser.add_argument('-s', '--static', dest='static', default=False, action='store_true', 
        help='Build static pages rather than hosting a dynamic webserver. [default=False]')
    args = parser.parse_args()
    
    host_cigma(args.pickle_file, static=args.static)
