#!/usr/bin/env python
# coding: utf-8

# # Importing Jupyter Notebooks as Modules

# It is a common problem that people want to import code from Jupyter Notebooks.
# This is made difficult by the fact that Notebooks are not plain Python files,
# and thus cannot be imported by the regular Python machinery.
# 
# Fortunately, Python provides some fairly sophisticated [hooks](https://www.python.org/dev/peps/pep-0302/) into the import machinery,
# so we can actually make Jupyter notebooks importable without much difficulty,
# and only using public APIs.

# In[1]:


import io, os, sys, types


# In[2]:


from IPython import get_ipython
from nbformat import read
from IPython.core.interactiveshell import InteractiveShell


# Import hooks typically take the form of two objects:
# 
# 1. a Module **Loader**, which takes a module name (e.g. `'IPython.display'`), and returns a Module
# 2. a Module **Finder**, which figures out whether a module might exist, and tells Python what **Loader** to use

# In[3]:


def find_notebook(fullname, path=None):
    """find a notebook, given its fully qualified name and an optional path

    This turns "foo.bar" into "foo/bar.ipynb"
    and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
    does not exist.
    """
    name = fullname.rsplit('.', 1)[-1]
    if not path:
        path = ['']
    for d in path:
        nb_path = os.path.join(d, name + ".ipynb")
        if os.path.isfile(nb_path):
            return nb_path
        # let import Notebook_Name find "Notebook Name.ipynb"
        nb_path = nb_path.replace("_", " ")
        if os.path.isfile(nb_path):
            return nb_path


# ## Notebook Loader

# Here we have our Notebook Loader.
# It's actually quite simple - once we figure out the filename of the module,
# all it does is:
# 
# 1. load the notebook document into memory
# 2. create an empty Module
# 3. execute every cell in the Module namespace
# 
# Since IPython cells can have extended syntax,
# the IPython transform is applied to turn each of these cells into their pure-Python counterparts before executing them.
# If all of your notebook cells are pure-Python,
# this step is unnecessary.

# In[4]:


class NotebookLoader(object):
    """Module Loader for Jupyter Notebooks"""

    def __init__(self, path=None):
        self.shell = InteractiveShell.instance()
        self.path = path

    def load_module(self, fullname):
        """import a notebook as a module"""
        path = find_notebook(fullname, self.path)

        print("importing Jupyter notebook from %s" % path)

        # load the notebook object
        with io.open(path, 'r', encoding='utf-8') as f:
            nb = read(f, 4)

        # create the module and add it to sys.modules
        # if name in sys.modules:
        #    return sys.modules[name]
        mod = types.ModuleType(fullname)
        mod.__file__ = path
        mod.__loader__ = self
        mod.__dict__['get_ipython'] = get_ipython
        sys.modules[fullname] = mod

        # extra work to ensure that magics that would affect the user_ns
        # actually affect the notebook module's ns
        save_user_ns = self.shell.user_ns
        self.shell.user_ns = mod.__dict__

        try:
            for cell in nb.cells:
                if cell.cell_type == 'code':
                    # transform the input to executable Python
                    code = self.shell.input_transformer_manager.transform_cell(cell.source)
                    # run the code in themodule
                    exec(code, mod.__dict__)
        finally:
            self.shell.user_ns = save_user_ns
        return mod

