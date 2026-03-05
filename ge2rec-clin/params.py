import nibabel as nib
import re
import logging

from useful import get_value_json

logger = logging.getLogger(__name__)


def get_acquisition_info(fmri_files, anat_file):
    acq_info = {}

    json_path =  anat_file.replace("nii.gz", "json").replace("nii", "json")
    manufacturer = get_value_json(json_path, "Manufacturer")
    model = get_value_json(json_path, "ManufacturersModelName")
    site = get_value_json(json_path, "InstitutionName")
    soft = get_value_json(json_path, "SoftwareVersions")
    
    img = nib.load(anat_file)
    data = img.get_fdata()
    shape = data.shape
    acq_info["anat"] = {
            "tr": get_value_json(json_path, "RepetitionTime"),
            "te": get_value_json(json_path, "EchoTime"),
            "voxel_size": img.header.get_zooms(),
            "num_slice": shape[2], 
            "pulse_seq_name": get_value_json(json_path, "PulseSequenceName"),
            "slice_thickness": get_value_json(json_path, "SliceThickness"),
            "fa": get_value_json(json_path, "FlipAngle"),
            "description": get_value_json(json_path, "SeriesDescription"),

        }

    all_repetition_time = []
    all_num_slices = []
    all_voxel_size = []

    for fmri_file in fmri_files:
        task = re.search(r"task-([^_]+)", fmri_file).group(1)
        json_path = fmri_file.replace("nii.gz", "json").replace("nii", "json")
        tr = get_value_json(json_path, "RepetitionTime")
        all_repetition_time.append(tr)
        img = nib.load(fmri_file)
        data = img.get_fdata()
        all_voxel_size.append(img.header.get_zooms())
        shape = data.shape
        all_num_slices.append(shape[2])

        acq_info[task] = {
            "tr": tr,
            "te": get_value_json(json_path, "EchoTime"),
            "voxel_size": img.header.get_zooms(),
            "num_slice": shape[2], 
            "pulse_seq_name": get_value_json(json_path, "PulseSequenceName"),
            "slice_thickness": get_value_json(json_path, "SliceThickness"),
            "fa": get_value_json(json_path, "FlipAngle"),
            "description": get_value_json(json_path, "SeriesDescription"),

        }
     # Check consistency
    if len(set(all_repetition_time)) != 1:
        logger.error(f"Inconsistent RepetitionTimes found: {all_repetition_time}")
        raise ValueError("All fMRI files must have the same RepetitionTime (TR).")

    if len(set(all_num_slices)) != 1:
        logger.error(f"Inconsistent number of slices found: {all_num_slices}")
        raise ValueError("All fMRI files must have the same number of slices.")

    # Check voxel size consistency with a tolerance (floating point rounding)
    first_voxel = all_voxel_size[0]
    for i, vox in enumerate(all_voxel_size):
        if not all(abs(v - fv) < 1e-5 for v, fv in zip(vox, first_voxel)):
            logger.error(f"Inconsistent voxel sizes found in file {fmri_files[i]}: {vox} vs {first_voxel}")
            raise ValueError("All fMRI files must have the same voxel size.")

    acq_info["general"] = {
        "mri": manufacturer + " " + model,
        "soft": soft,
        "site": site,
        "tr": all_repetition_time[0],
        "num_slices":  all_num_slices[0],
        "voxel_size_round": [round(all_voxel_size[0][0]), round(all_voxel_size[0][1]), round(all_voxel_size[0][2])]

    }

    logger.info(f"Acquisition info: {acq_info}")
    return acq_info
