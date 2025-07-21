```
ModuleExample/
├── app/
│   ├── entrypoint.py              # main module entry point
│   └── ...                        # other Python source files
│
├── bin/
│   ├── run_module.cmd             # Windows command script to run the module
│   ├── run_module_with_flask.cmd  # run module through Flask API
│   └── ...                        # other executable scripts
│
├── logs/
│   └── (log files go here)        # runtime logs, typically gitignored
│
├── data/                          # all data files (input and output)
│   ├── input/                     # input files
│   │   └── (additional input data files)
│   ├── input_from_FEWS/
│   │   └── (exported files by FEWS, required as input for the module)
│   ├── output/                    # output files
│   │   └── (other generated output files)
│   └── output_to_FEWS/
│       └── (exported files/timeseries for FEWS import)
│
├── tests/
│   ├── __init__.py                # optional, if tests are packaged
│   ├── test_module.py             # unit/integration tests
│   └── ...                        # additional test files
│
├── README.md                      # project overview
└── .gitignore                     # git ignore rules
```