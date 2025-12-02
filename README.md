# BlooP/FlooP interpreter
This is an interpreter for the BlooP and FlooP languages defined in Douglas R. Hofstadter's GEB book. It is a quick and dirty implementation coded in a few hours for a demonstration. It probably WILL NOT run your programs. You have been warned.

# Dependencies
- python
- lark-parser python package

I highly recommend creating a venv:
```sh
# In this repo's root folder
python -m venv venv
source venv/bin/activate
pip install lark-parser
```

# Running
The interpreter accepts a filepath as a positional argument.
```sh
python floop.py <program.floop>
```

If you use a venv:
```sh
# In this repo's root folder
source venv/bin/activate
python floop.py <program.floop>
```

# Examples
There are a few example programs in the `/examples` directory.
