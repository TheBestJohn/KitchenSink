
# Configuration file for the Sphinx documentation builder.

import os
import sys

# -- Path setup --------------------------------------------------------------
# Make sure the project root is in the path
sys.path.insert(0, os.path.abspath('../..'))


# -- Project information -----------------------------------------------------
project = 'KitchenSink Audio'
copyright = '2024, TheBestJohn'
author = 'TheBestJohn'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',      # Core library for autodoc
    'sphinx.ext.napoleon',     # Support for Google-style docstrings
    'sphinx.ext.viewcode',     # Add links to source code
    'myst_parser',             # To parse Markdown files like README.md
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
html_theme = 'furo'
html_static_path = ['_static']

# -- Autodoc settings --------------------------------------------------------
autodoc_typehints = "description"
autodoc_class_signature = "separated"
