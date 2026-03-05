Table of contents
1. [Overview](#overview)
2. [Installation and configuration](#installation)
3. [How it works](#how-it-works)
4. [License](#license)

<a name="overview"></a>
# Overview
GE2REC-Clin is an fMRI processing pipeline dedicated to the GE2REC protocol, with a graphical user interface.

It provides a simple interface to:
- Import DICOM data (ZIP format) and convert it to BIDS format or use data already organized in BIDS format
- Run SPM preprocessing
- Perform first-level statistical analysis
- Automatically generate a report

## About the GE2REC Protocol

The GE2REC protocol consists of three interdependent tasks: 
- GE – Sentence generation with implicit encoding ("génération") 
- RECO – Recognition task ("reconnaissance")
- RE – Recall task ("rappel")

This protocol allows the interaction of language and memory functions (LMN language memory network) to be mapped at the individual level. 
It provides a comprehensive assessment including verbal and visual modalities and various language processes.

References:

- Banjac S, Roger E, Cousin E, Mosca C, Minotti L, Krainik A, Kahane P, Baciu M. Mapping of Language-and-Memory Networks in Patients With Temporal Lobe Epilepsy by Using the GE2REC Protocol. Front Hum Neurosci. 2022 Jan 6;15:752138. doi: 10.3389/fnhum.2021.752138. PMID: 35069148; PMCID: PMC8772037.
- Banjac, S., Roger, E., Cousin, E., Perrone-Bertolotti, M., Haldin, C., Pichat, C., et al. (2020). Interactive mapping of language and memory with the GE2REC protocol. Brain Imaging Behav. 15, 1562–1579. doi: 10.1007/s11682-020-00355-x

## Important note
This module uses patient name and birth date available in DICOM metadata to generate BIDS identifiers.

If anonymized data are required, DICOM files must be anonymized before using this module.

## Limitations: 
- Designed specifically for GE2REC protocol (adaptation required for other paradigms)
- Assumes a valid DICOM ZIP structure
- Requires a correct SPM installation
- Protocol naming and generated report are currently in French


<a name="installation"></a>
## Installation and configuration

### Clone this repository

```bash
git clone git@github.com:IRMaGe-3T/ge2rec-clin.git
```
## Requirements

- [SPM](https://www.fil.ion.ucl.ac.uk/spm/) installed and Matlab configured 
- [dcm2niix](https://github.com/rordenlab/dcm2niix/releases) (release >=version 20-july-2022)
- Python dependencies (see [pyproject](./pyproject.toml))

### Install python requirements

```bash
cd /ge2rec-clin/
pip install -e .
```

### Configure `config/config.json`

Specify the following path in the configuration file:
- OutputDirectory = path to BIDS directory, tha rawdata will be added in /OutputDirectory/sub-*/ses*/ and the processing in /OutputDirectory/derivatives/sub-*/ses-*/
- BidsConfigFile = path to dcm2bids config file
- WorkingDirectory = path to working directory (only used for temporary files)
- SPMPath = path to spm 

Example:

```bash
{
    "OutputDirectory": "/path/to/bids/directory",
    "BidsConfigFile": "/path/to/bidsd_dcm2bids_config_template.json",
    "WorkingDirectory": "/path/to/working/directory",
    "SPMPath": "/path/to/spm"
}
````

<a name="how-it-works"></a>
# How it works


## Run  the application

1. Launch the module

```bash
    python /ge2rec-clin/ge2rec-clin/main.py
```
2. Import data (DICOM import or BIDS import)
    - DICOM Import: 
    
        Select a ZIP directory with your DICOM (select "Open.." button). DICOM data will be converted to BIDS format

    - BIDS Import: 
        
        If your data are already in your BIDS directory, fill subject and session tag

    Required data: one anatomical run  (T1w) and GE2REC functional runs.

3. Acquisition information: 
    
    Select acquisition type for slice timing correction:
        - sequential ascending: acquisition in linear order from foot to head or from anterior to posterior or from left to right
        - sequential descending: acquisition in linear order from head to foot or from posterior to anterior or from right to left

4. Patient information:

    Fill patient information (age, sex, pathology, pathology lateralization)

5. Click the "RUN" button.

## Workflow description
### Data conversion

- DICOM Import: 

    You only need to give the DICOM directory path and the module will organize your data in BIDS (using [dcm2bids](https://unfmontreal.github.io/Dcm2Bids)). A [dcm2bids configuration file](https://unfmontreal.github.io/Dcm2Bids/3.1.1/how-to/create-config-file/) should be specified in the `BidsConfigFile` field in the [configuration file](./config/config.json). The BIDS subject name is composed of the DICOM tag (0x10, 0x0010) (patient's name) and the DICOM tag (0x10, 0x0030) (patient's date of birth). The tag (0x08, 0x0020) (study date) is used for the BIDS session name. If you want anonymised data, you will need to anonymise your DICOM before to use this module. 

    Functionnal run will be renamed following BIDS architecture with the following field for "task" suffix:
    - "gene" for the "génération" task
    - "reco for the "reconnaisance" task
    - "rappel" for the "rappel task 

    Template events files that describe stimulus are used.

- BIDS Import: the subject should already be in your BIDS directory (see Configuration section) and functional runs must use the task naming described above. Existing events files will be used if available.
Otherwise, template events files will be generated.

The application requires at least one functional run.


### Processing
The processing are done with SPM. Functional runs are realigned and slice timing correction is done. Anatomical data are co-register with mean functional, corrected for bias and normalized to MNI
(Montreal Neurological Institute) space. The anatomical normalization parameters were subsequently used for the normalization of functional runs. 
Each functional run was smoothed by an 6 mm FWHM Gaussian kernel. Noise and signal drift was removed by using a high-pass filter (1/128 Hz cutoff).
Preprocessed data were then statistically analyzed.

For "génération" task, a quantitative evaluation is done using the LI toolbox  (Wilke, Marko, and Karen Lidzba. 'LI-Tool: A New Toolbox to Assess Lateralization in
Functional MR-Data.' Journal of Neuroscience Methods 163, no. 1 (June 15, 2007): 128–36.
https://doi.org/10.1016/j.jneumeth.2007.01.026. ) 

### Outputs

All the outputs are in the directory `/path/to/bids/directory/derivatives/sub-*/ses-*/`.

A report with the folowing information is generated:
- patients and acquistions information
- statistical map for langage production
- quantitative evaluation of the langage production using LI Toolbox
- statistical map for memory recognition
- statistical map for memory recall
- quality control for anatomical data 
- quality control for functional data


<a name="license"></a>
# License

TO FILL 
