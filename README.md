## Prepare venv

```
sudo apt install rustc
sudo apt install python3-venv
cd <SRCDIR>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

# Run the app

```
cd flaskr
export PYTHONPATH=path/to/qseq
flask run --debug
http://127.0.0.1:5000/
```

.seq file have to be in resources repository

click on one of the sequences file name to see is sequence
click on "add file" then put the name of the sequence file you want to add (example : 'tempmess.seq')
