from abaqus import *
from abaqusConstants import *
import visualization

import column_part
import soil_part
import _materials
import sections_profiles
import _steps
import _assembly
import _interactions
import _mesh
import _loads
import _jobs
import output


class NumericalSystem:

    def __init__(self, materials, super_str, foundation, results_dir, analysisname):

        ''' ---------- Variables ---------- '''

        # soil
        self.pile_soil_space = 5
        self.soil_depth = foundation.h + self.pile_soil_space
        self.soil_diameter = 3.0 * super_str.h
        self.infinites_width = 2
        self.infinites_bottom = False
        self.fixed_sides = False
        self.contact_col_soil = True # False -> tie constraints, True -> contact

        # mesh
        self.col_mesh_size = 3
        self.soil_mesh_size = 7
        self.contact_mesh_size = 2

        # frequency analysis
        self.numEigen = 2  # number of eigenvalue to search for
        self.minEigen = 1  # minimal frequency of interest
        self.maxEigen = 50  # max

        # modal dynamics
        self.direct_damping_ratio = 0.0

        # software specific
        self.results_dir = results_dir
        self.analysisname = analysisname

        ''' ---------- Create Abaqus Model ---------- '''

        # create model
        mdb.Model(name='3D_MODEL')

        # create materials
        for mat in materials:
            _materials.create(mat)

        # create parts
        # soil
        soil_part.create_part(self.soil_diameter, self.soil_depth)
        soil_part.cut_extrude(super_str.sec.d_e, super_str.sec.t, foundation.h)

        soil_part.partition_side_infinite(self.soil_diameter - self.infinites_width)
        soil_part.partition_bottom(space=self.pile_soil_space)

        # column
        column_part.create_part(super_str, foundation)
        column_part.partition(foundation)


        # create sections and profiles
        sections_profiles.create_column_section()
        sections_profiles.create_soil_section()


        # assign sections
        sections_profiles.assign_section()


        # steps
        _steps.create_frequency(self.numEigen, self.minEigen, self.maxEigen)
        _steps.create_ini_disp()
        _steps.create_modal_dynamics(1, 0.01)
        _steps.set_direct_damping(1, 5, self.direct_damping_ratio)


        # assembly
        _assembly.assemble_parts(self.soil_depth, foundation.h)

        # apply interactions
        _interactions.interaction_soil_col(self.contact_col_soil)


        # mesh
        _mesh.assign_properties(self.infinites_bottom) # assign tet elements to finite soil part and column
        _mesh.infinite_elements(self.fixed_sides)
        _mesh.seed(self.col_mesh_size, self.soil_mesh_size, self.contact_mesh_size)
        _mesh.mesh_parts()


        # bc, constraints and loads.py
        _loads.fix_base_bc()
        if self.fixed_sides:
            _loads.fix_sides_bc()
        _loads.ini_disp(super_str.h / 300.0)
        _loads.gravity()


        # job

        self.jobname = 'job_infinite_' + self.analysisname

        _jobs.create_job('3D_MODEL', 'job_acoustic')
        _jobs.modify_input_file(self.jobname) # change AC3D8 to CIN3D8 element type
        _jobs.import_input(self.jobname)
        _jobs.create_job('Infinite_MODEL', self.jobname)

    def run_analysis(self):

        job = mdb.jobs[self.jobname]
        job.submit(consistencyChecking=OFF)
        job.waitForCompletion()


    def output(self):

        odb = output.load_odb(self.jobname)
        output.plot_top_disp(self.results_dir, self.analysisname, odb)
        output.visual(self.results_dir, self.analysisname)
        #odb.close(odb, write=TRUE)

    def delete_model(self):
        del mdb.models['3D_MODEL']
