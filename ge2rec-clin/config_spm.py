
from nipype.interfaces.matlab import MatlabCommand


def configure_spm(spm_path):
    """Configure SPM path for Nipype."""
    MatlabCommand.set_default_paths(spm_path)
    MatlabCommand.set_default_matlab_cmd("matlab -nodesktop -nosplash")

