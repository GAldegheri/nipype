import os
from pathlib import Path

from nipype.interfaces.base import File, InputMultiPath, TraitedSpec, traits, isdefined
from nipype.interfaces.cat12.base import NestedCell, Cell
from nipype.interfaces.spm import SPMCommand
from nipype.interfaces.spm.base import SPMCommandInputSpec
from nipype.utils.filemanip import split_filename


class ExtractAdditionalSurfaceParametersInputSpec(SPMCommandInputSpec):
    left_central_surfaces = InputMultiPath(
        File(exists=True),
        field="data_surf",
        desc="Left and central surfaces files",
        mandatory=True,
        copyfile=False,
    )
    surface_files = InputMultiPath(
        File(exists=True), desc="All surface files", mandatory=False, copyfile=False
    )

    gyrification = traits.Bool(
        True,
        field="GI",
        usedefault=True,
        desc="Extract gyrification index (GI) based on absolute mean curvature. The"
        " method is described in Luders et al. Neuroimage, 29:1224-1230, 2006",
    )
    gmv = traits.Bool(True, field="gmv", usedefault=True, desc="Extract volume")
    area = traits.Bool(True, field="area", usedefault=True, desc="Extract area surface")
    depth = traits.Bool(
        False,
        field="SD",
        usedefault=True,
        desc="Extract sulcus depth based on euclidean distance between the central "
        "surface anf its convex hull.",
    )
    fractal_dimension = traits.Bool(
        False,
        field="FD",
        usedefault=True,
        desc="Extract cortical complexity (fractal dimension) which is "
        "described in Yotter ar al. Neuroimage, 56(3): 961-973, 2011",
    )


class ExtractAdditionalSurfaceParametersOutputSpec(TraitedSpec):
    lh_extracted_files = traits.List(
        File(exists=True), desc="Files of left Hemisphere extracted measures"
    )
    rh_extracted_files = traits.List(
        File(exists=True), desc="Files of right Hemisphere extracted measures"
    )

    lh_gyrification = traits.List(
        File(exists=True), desc="Gyrification of left Hemisphere"
    )
    rh_gyrification = traits.List(
        File(exists=True), desc="Gyrification of right Hemisphere"
    )

    lh_gmv = traits.List(
        File(exists=True), desc="Grey matter volume of left Hemisphere"
    )
    rh_gmv = traits.List(
        File(exists=True), desc="Grey matter volume of right Hemisphere"
    )

    lh_area = traits.List(File(exists=True), desc="Area of left Hemisphere")
    rh_area = traits.List(File(exists=True), desc="Area of right Hemisphere")

    lh_depth = traits.List(File(exists=True), desc="Depth of left Hemisphere")
    rh_depth = traits.List(File(exists=True), desc="Depth of right Hemisphere")

    lh_fractaldimension = traits.List(
        File(exists=True), desc="Fractal Dimension of left Hemisphere"
    )
    rh_fractaldimension = traits.List(
        File(exists=True), desc="Fractal Dimension of right Hemisphere"
    )


class ExtractAdditionalSurfaceParameters(SPMCommand):
    """
    Additional surface parameters can be extracted that can be used for statistical analysis, such as:

    * Central surfaces
    * Surface area
    * Surface GM volume
    * Gyrification Index
    * Sulcus depth
    * Toro's gyrification index
    * Shaer's local gyrification index
    * Laplacian gyrification indices
    * Addicional surfaces
    * Measure normalization
    * Lazy processing

    http://www.neuro.uni-jena.de/cat12/CAT12-Manual.pdf#page=53

    Examples
    --------
    >>> # Set the left surface files, both will be processed
    >>> lh_path_central = 'lh.central.structural.gii'
    >>> # Put here all surface files generated by CAT12 Segment, this is only required if the this approach is putted in
    >>> surf_files = ['lh.sphere.reg.structural.gii', 'rh.sphere.reg.structural.gii', 'lh.sphere.structural.gii', 'rh.sphere.structural.gii', 'rh.central.structural.gii', 'lh.pbt.structural', 'rh.pbt.structural']
    >>> extract_additional_measures = ExtractAdditionalSurfaceParameters(left_central_surfaces=lh_path_central, surface_files=surf_files)
    >>> extract_additional_measures.run() # doctest: +SKIP

    """

    input_spec = ExtractAdditionalSurfaceParametersInputSpec
    output_spec = ExtractAdditionalSurfaceParametersOutputSpec

    def __init__(self, **inputs):
        _local_version = SPMCommand().version
        if _local_version and "12." in _local_version:
            self._jobtype = "tools"
            self._jobname = "cat.stools.surfextract"

        super().__init__(**inputs)

    def _list_outputs(self):
        outputs = self._outputs().get()

        names_outputs = [
            (self.inputs.gyrification, "gyrification"),
            (self.inputs.gmv, "gmv"),
            (self.inputs.area, "area"),
            (self.inputs.depth, "depth"),
            (self.inputs.fractal_dimension, "fractaldimension"),
        ]

        for filename in self.inputs.left_central_surfaces:
            pth, base, ext = split_filename(filename)
            # The first part of the filename is rh.central or lh.central
            original_filename = base.split(".", 2)[-1]
            for extracted_parameter, parameter_name in names_outputs:
                if extracted_parameter:
                    for hemisphere in ["rh", "lh"]:
                        all_files_hemisphere = hemisphere + "_extracted_files"
                        name_hemisphere = hemisphere + "_" + parameter_name
                        if not isdefined(outputs[name_hemisphere]):
                            outputs[name_hemisphere] = []
                        if not isdefined(outputs[all_files_hemisphere]):
                            outputs[all_files_hemisphere] = []
                        generated_filename = ".".join(
                            [hemisphere, parameter_name, original_filename]
                        )
                        outputs[name_hemisphere].append(
                            os.path.join(pth, generated_filename)
                        )

                        # Add all hemisphere files into one list, this is important because only the left hemisphere
                        # files are used as input in the Surface ROI Tools, for instance.
                        outputs[all_files_hemisphere].append(
                            os.path.join(pth, generated_filename)
                        )

        return outputs

    def _format_arg(self, opt, spec, val):
        if opt == "left_central_surfaces":
            return Cell2Str(val)
        return super()._format_arg(opt, spec, val)


class ExtractROIBasedSurfaceMeasuresInputSpec(SPMCommandInputSpec):
    # Only these files are given as input, yet the right hemisphere (rh) files should also be on the processing
    # directory.

    surface_files = InputMultiPath(
        File(exists=True),
        desc="Surface data files. This variable should be a list with all",
        mandatory=False,
        copyfile=False,
    )
    lh_roi_atlas = InputMultiPath(
        File(exists=True),
        field="rdata",
        desc="(Left) ROI Atlas. These are the ROI's ",
        mandatory=True,
        copyfile=False,
    )

    rh_roi_atlas = InputMultiPath(
        File(exists=True),
        desc="(Right) ROI Atlas. These are the ROI's ",
        mandatory=False,
        copyfile=False,
    )

    lh_surface_measure = InputMultiPath(
        File(exists=True),
        field="cdata",
        desc="(Left) Surface data files. ",
        mandatory=True,
        copyfile=False,
    )
    rh_surface_measure = InputMultiPath(
        File(exists=True),
        desc="(Right) Surface data files.",
        mandatory=False,
        copyfile=False,
    )


class ExtractROIBasedSurfaceMeasuresOutputSpec(TraitedSpec):
    label_files = traits.List(
        File(exists=True), desc="Files with the measures extracted for ROIs."
    )


class ExtractROIBasedSurfaceMeasures(SPMCommand):
    """
    Extract ROI-based surface values
    While ROI-based values for VBM (volume) data are automatically saved in the ``label`` folder as XML file it is
    necessary to additionally extract these values for surface data (except for thickness which is automatically
    extracted during segmentation). This has to be done after preprocessing the data and creating cortical surfaces.

    You can extract ROI-based values for cortical thickness but also for any other surface parameter that was extracted
    using the Extract Additional Surface Parameters such as volume, area, depth, gyrification and fractal dimension.


     http://www.neuro.uni-jena.de/cat12/CAT12-Manual.pdf#page=53

     Examples
     --------
    >>> # Template surface files
    >>> lh_atlas = 'lh.aparc_a2009s.freesurfer.annot'
    >>> rh_atlas = 'rh.aparc_a2009s.freesurfer.annot'
    >>> surf_files = ['lh.sphere.reg.structural.gii', 'rh.sphere.reg.structural.gii', 'lh.sphere.structural.gii', 'rh.sphere.structural.gii', 'lh.central.structural.gii', 'rh.central.structural.gii', 'lh.pbt.structural', 'rh.pbt.structural']
    >>> lh_measure = 'lh.area.structural'
    >>> extract_additional_measures = ExtractROIBasedSurfaceMeasures(surface_files=surf_files, lh_surface_measure=lh_measure, lh_roi_atlas=lh_atlas, rh_roi_atlas=rh_atlas)
    >>> extract_additional_measures.run() # doctest: +SKIP


    """

    input_spec = ExtractROIBasedSurfaceMeasuresInputSpec
    output_spec = ExtractROIBasedSurfaceMeasuresOutputSpec

    def __init__(self, **inputs):
        _local_version = SPMCommand().version
        if _local_version and "12." in _local_version:
            self._jobtype = "tools"
            self._jobname = "cat.stools.surf2roi"

        SPMCommand.__init__(self, **inputs)

    def _format_arg(self, opt, spec, val):
        if opt == "lh_surface_measure":
            return NestedCell(val)
        elif opt == "lh_roi_atlas":
            return Cell2Str(val)

        return super()._format_arg(opt, spec, val)

    def _list_outputs(self):
        outputs = self._outputs().get()

        pth, base, ext = split_filename(self.inputs.lh_surface_measure[0])

        outputs["label_files"] = [
            str(label) for label in Path(pth).glob("label/*") if label.is_file()
        ]
        return outputs


class Cell2Str(Cell):
    def __str__(self):
        """Convert input to appropriate format for cat12"""
        return "{%s}" % self.to_string()