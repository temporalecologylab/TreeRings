# No Hardware Stitching Example

Tested on Windows 11 with Python 3.15.2.

1. Install Python 3.15.2 for Windows by following Python's guidelines. (https://www.python.org/downloads/)
2. Open 'Command Prompt'

3. Navigate to the `./TreeRings/code/no_hardware_stitching_example` directory.
`> cd ./TreeRings/code/no_hardware_stitching_example`

4. Create a virtual environment.
`> py -3.15 -m venv no_hardware_stitching_example`

5. Activate the virtual environment in your terminal. There should now be a prefix of `(no_hardware_stitching_example)` on your Command Prompt line.
`> no_hardware_stitching_example\Scripts\activate`

6. Install the dependencies.
`> pip install -r no_hardware_stitching_requirements.txt`

7. Navigate to the ./TreeRings/code directory.
`> cd ..`

8. Run the stitcher program which has been configured to stitch the example dataset.
`> python stitcher.py`

At the bottom of `stitcher.py` you can change the resize values by adding or removing values between 0.1 and 1.0 to the `sizes` list. A new folder will be created for each resize value in the list inside the `./TreeRings/code/no_hardware_stitching_example` directory.