from nipype.interfaces.matlab import MatlabCommand
from nipype.interfaces import spm
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

                cmd_spm_stand = f"{spm_standalone_script_path} {mcr_path} script"
                os.environ["SPMMCRCMD"] = cmd_spm_stand
                os.environ["FORCE_SPMMCR"] = "1"
                spm.SPMCommand.set_mlab_paths(matlab_cmd=cmd_spm_stand, use_mcr=True)

                print("SPM Standalone configuration selected.")
                print(f"SPM version detected by Nipype: {spm.SPMCommand().version}")
                return

    # Fallback to SPM with MATLAB
    if spm_path and os.path.isdir(spm_path):
        os.environ.pop("SPMMCRCMD", None)
        os.environ.pop("FORCE_SPMMCR", None)
        MatlabCommand.set_default_paths(spm_path)
        MatlabCommand.set_default_matlab_cmd("matlab -nodesktop -nosplash")
        print("SPM with MATLAB configuration selected.")
        print(f"SPM version detected by Nipype: {spm.SPMCommand().version}")
        return

    raise ValueError(
        "No valid SPM installation found. "
        f"SPMPath: {spm_path}, "
        f"SPMStandalonePath: {spm_standalone_script_path}, "
        f"MCRPath: {mcr_path}"
    )
