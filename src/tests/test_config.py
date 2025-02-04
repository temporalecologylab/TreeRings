import tim.utils
import pytest 


@pytest.fixture
def config_data_from_file(dir = "./src/tim/"):
    return tim.utils.load_config(dir)

def test_camera_types_int(config_data_from_file):
    assert type(config_data_from_file["camera"]["CROP_H"]) == int
    assert type(config_data_from_file["camera"]["CROP_W"]) == int
    assert type(config_data_from_file["camera"]["W_PIXELS_NO_CROP"]) == int
    assert type(config_data_from_file["camera"]["H_PIXELS_NO_CROP"]) == int

def test_controller_types_int(config_data_from_file):
    assert type(config_data_from_file["controller"]["N_IMAGES_MULTIPLE_DISTANCES"]) == int
    assert type(config_data_from_file["controller"]["SLOW_FEED_RATE_XY"]) == int
    assert type(config_data_from_file["controller"]["SLOW_FEED_RATE_Z"]) == int
    assert type(config_data_from_file["controller"]["FAST_FEED_RATE_XY"]) == int
    assert type(config_data_from_file["controller"]["FAST_FEED_RATE_Z"]) == int
    assert type(config_data_from_file["controller"]["N_IMAGES_CORE_CENTERING"]) == int

def test_controller_types_float(config_data_from_file):
    assert type(config_data_from_file["controller"]["HEIGHT_RANGE_MM"]) == float or  type(config_data_from_file["controller"]["HEIGHT_RANGE_MM"]) == int
    assert type(config_data_from_file["controller"]["ACCELERATION_BUFFER_MM"]) == float or type(config_data_from_file["controller"]["ACCELERATION_BUFFER_MM"]) == int
    assert type(config_data_from_file["controller"]["CORE_CENTERING_RANGE"]) == float or type(config_data_from_file["controller"]["CORE_CENTERING_RANGE"]) == int
    
def test_controller_types_list(config_data_from_file):
    assert type(config_data_from_file["controller"]["STITCH_SIZES"]) == list

def test_focus_types_float(config_data_from_file):
    assert type(config_data_from_file["focus"]["PID_SCALE_FACTOR"]) == float
    assert type(config_data_from_file["focus"]["Kp"]) == float or type(config_data_from_file["focus"]["Kp"]) == int
    assert type(config_data_from_file["focus"]["Ki"]) == float or type(config_data_from_file["focus"]["Ki"]) == int
    assert type(config_data_from_file["focus"]["Kd"]) == float or type(config_data_from_file["focus"]["Kd"]) == int
    assert type(config_data_from_file["focus"]["BACKGROUND_STD_THRESHOLD"]) == float

def test_gantry_types_float_or_int(config_data_from_file):
    assert type(config_data_from_file["gantry"]["FEED_RATE_DEFAULT_XY"]) == int
    assert type(config_data_from_file["gantry"]["FEED_RATE_DEFAULT_Z"]) == int

def test_gui_types_list(config_data_from_file):
    assert type(config_data_from_file["gui"]["DEFAULT_WINDOW_SIZE"]) == list

def test_gui_types_float_or_int(config_data_from_file):
    assert type(config_data_from_file["gui"]["DEFAULT_SAMPLE_HEIGHT_MM"]) == int or type(config_data_from_file["gui"]["DEFAULT_SAMPLE_HEIGHT_MM"]) == float
    assert type(config_data_from_file["gui"]["DEFAULT_SAMPLE_WIDTH_MM"]) == int or type(config_data_from_file["gui"]["DEFAULT_SAMPLE_WIDTH_MM"]) == float
    assert type(config_data_from_file["gui"]["DEFAULT_IMAGE_HEIGHT_MM"]) == int or type(config_data_from_file["gui"]["DEFAULT_IMAGE_HEIGHT_MM"]) == float
    assert type(config_data_from_file["gui"]["DEFAULT_IMAGE_WIDTH_MM"]) == int or type(config_data_from_file["gui"]["DEFAULT_IMAGE_WIDTH_MM"]) == float
    assert type(config_data_from_file["gui"]["DEFAULT_JOG_DISTANCE"]) == int or type(config_data_from_file["gui"]["DEFAULT_JOG_DISTANCE"]) == float
    assert type(config_data_from_file["gui"]["DEFAULT_PERCENT_OVERLAP"]) == int or type(config_data_from_file["gui"]["DEFAULT_PERCENT_OVERLAP"]) == float
    
def test_gui_types_int(config_data_from_file):
    assert type(config_data_from_file["gui"]["DEFAULT_ZOOM_LEVEL"]) == int 
    
def test_gui_types_float_or_int(config_data_from_file):
    assert type(config_data_from_file["stitcher"]["MAX_FILE_SIZE_GB"]) == int or type(config_data_from_file["stitcher"]["MAX_FILE_SIZE_GB"]) == float
    