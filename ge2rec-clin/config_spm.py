from nipype.interfaces.matlab import MatlabCommand
import os


def configure_spm(spm_path=None, spm_standalone_script_path=None, mcr_path=None):
    """Configure SPM for Nipype.

    SPM Standalone takes priority over SPM with MATLAB.
    """

    # Try SPM Standalone first
    if spm_standalone_script_path and os.path.isfile(spm_standalone_script_path):

        if not mcr_path or not os.path.isdir(mcr_path):
            print("SPM Standalone found, but MCRPath is missing or invalid.")
        else:
            if os.path.isfile(spm_standalone_script_path):
                MatlabCommand.set_default_paths(spm_standalone_script_path)
                MatlabCommand.set_default_matlab_cmd(
                    f"{spm_standalone_script_path} {mcr_path} script"
                )
                print("SPM Standalone configuration selected.")
                return

    # Fallback to SPM with MATLAB
    if spm_path and os.path.isdir(spm_path):
        MatlabCommand.set_default_paths(spm_path)
        MatlabCommand.set_default_matlab_cmd("matlab -nodesktop -nosplash")
        print("SPM with MATLAB configuration selected.")
        return

    raise ValueError(
        "No valid SPM installation found. "
        f"SPMPath: {spm_path}, "
        f"SPMStandalonePath: {spm_standalone_script_path}, "
        f"MCRPath: {mcr_path}"
    )