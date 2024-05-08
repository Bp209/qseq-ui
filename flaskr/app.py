import sqlite3
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
from .qseq.sequencer import Sequencer  # type: ignore


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'


@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    return render_template('index.html', posts=posts)


@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)


@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('create.html')


@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('UPDATE posts SET title = ?, content = ?'
                         ' WHERE id = ?',
                         (title, content, id))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))


class File_value():
    def __init__(self, filepath):

        self.sequence(filepath)

    def sequence(self, file):
        file_dir = '../sequence/'+file  # directory where sequence file is located # noqa E501
        sequences = Sequencer()
        sequences.load_sequence_file(file_dir)
        Timestamps = ''
        method = ''
        status = ''
        for line in sequences.schedule:
            Timestamps = Timestamps + (str(line).split('SequenceStep')[1].split('=')[1].split(',')[0]) + ':' # noqa E501
            method = method + (str(line).split('SequenceStep')[1].split('=')[2].replace("'", "").replace('(', '').replace(')', '')) + ':' # noqa E501
            status = status + ('waiting') + ':'
        print(Timestamps)
        self.Timestamps = Timestamps.split(':') # noqa E501
        self.method = method.split(':')
        self.status = status.split(':')
        i = 1
        nb_value = list()
        while i < len(self.Timestamps):
            val = str(i)
            nb_value.append(val)
            i = i + 1
        self.tms = {a: [b, c, d] for a, b, c, d in zip(nb_value, self.Timestamps, self.method , self.status)} # noqa E501


@app.route('/<file>/sequence', methods=['GET', 'POST'])
def sequence_page(file):
    seq = File_value(file)
    seq.sequence(file)
    return render_template('sequence.html', sequence=seq) # noqa E501
