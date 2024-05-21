# -*- coding: utf-8 -*-
import unittest
import os  # noqa: F401
import json  # noqa: F401
import time
import requests  # noqa: F401
import inspect
import shutil
import uuid
from pathlib import Path
from unittest.mock import patch
import hashlib
import zipfile

from os import environ
try:
    from ConfigParser import ConfigParser  # py2
except:
    from configparser import ConfigParser  # py3

from pprint import pprint  # noqa: F401

from installed_clients.WorkspaceClient import Workspace as workspaceService
from kb_staging_exporter.kb_staging_exporterImpl import kb_staging_exporter
from kb_staging_exporter.kb_staging_exporterServer import MethodContext
from kb_staging_exporter.authclient import KBaseAuth as _KBaseAuth
from kb_staging_exporter.Utils.staging_downloader import staging_downloader
from installed_clients.ReadsUtilsClient import ReadsUtils
from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.GenomeFileUtilClient import GenomeFileUtil
from installed_clients.ReadsAlignmentUtilsClient import ReadsAlignmentUtils


class kb_staging_exporterTest(unittest.TestCase):

    READS_FASTQ_MD5 = '68442259e29e856f766bbe38fedd9b30'
    ASSEMLBY_FASTA_MD5 = 'a5cecffc35ef1cf86c6f7a6e1f72066e'
    GENOME_GENBANK_MD5 = '5d6150673c2b0445bf7912ff79ef82c7'
    ALIGNMENT_BAM_MD5 = '96c59589b0ed7338ff27de1881cf40b3'

    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_staging_exporter'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_staging_exporter',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = workspaceService(cls.wsURL)
        cls.serviceImpl = kb_staging_exporter(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']

        cls.ru = ReadsUtils(cls.callback_url)
        cls.au = AssemblyUtil(cls.callback_url)
        cls.gfu = GenomeFileUtil(cls.callback_url, service_ver='dev')
        cls.rau = ReadsAlignmentUtils(cls.callback_url)
        
        cls.wsName = "test_kb_staging_exporter_" + str(uuid.uuid4())
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})
        cls.wsid = ret[0]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def getWsClient(self):
        return self.__class__.wsClient

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx

    def md5(self, fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def loadGenome(self):
        if hasattr(self.__class__, 'test_Genome'):
            return self.__class__.test_Genome

        genbank_file_name = 'minimal.gbff'
        genbank_file_path = os.path.join(self.scratch, genbank_file_name)
        shutil.copy(os.path.join('data', genbank_file_name), genbank_file_path)

        genome_object_name = 'test_Genome'
        test_Genome = self.gfu.genbank_to_genome({'file': {'path': genbank_file_path},
                                                  'workspace_name': self.wsName,
                                                  'genome_name': genome_object_name,
                                                  'generate_ids_if_needed': 1
                                                  })['genome_ref']

        self.__class__.test_Genome = test_Genome
        print('Loaded Genome: ' + test_Genome)
        return test_Genome

    def loadMetagenome(self):
        if hasattr(self.__class__, 'test_Metagenome'):
            return self.__class__.test_Metagenome
        gff_file_name = 'metagenome.gff'
        gff_file_path = os.path.join(self.scratch, gff_file_name)
        fasta_file_name = 'metagenome.fa'
        fasta_file_path = os.path.join(self.scratch, fasta_file_name)

        curr_dir = os.path.dirname(os.path.abspath(__file__))

        files = os.listdir(os.path.join(curr_dir, 'data'))

        if not os.path.isfile(os.path.join(curr_dir, 'data', gff_file_name)):
            raise RuntimeError("cannot find file " + gff_file_name + f" -- {files}")
        if not os.path.isfile(os.path.join(curr_dir, 'data', fasta_file_name)):
            raise RuntimeError("cannot find file " + fasta_file_name + f" -- {files}")

        shutil.copy(os.path.join(curr_dir, 'data', gff_file_name), gff_file_path)
        shutil.copy(os.path.join(curr_dir, 'data', fasta_file_name), fasta_file_path)

        metagenome_object_name = 'test_Metagenome'
        test_Metagenome = self.gfu.fasta_gff_to_metagenome({'gff_file': {'path': gff_file_path},
                                                            'fasta_file': {'path': fasta_file_path},
                                                            'workspace_name': self.wsName,
                                                            'genome_name': metagenome_object_name,
                                                            'generate_missing_genes': 1
                                                            })['metagenome_ref']
        self.__class__.test_Metagenome = test_Metagenome
        print(f'Loaded Metagenome:  {test_Metagenome}')
        return test_Metagenome

    def loadReads(self):
        if hasattr(self.__class__, 'test_Reads'):
            return self.__class__.test_Reads

        fwd_reads_file_name = 'reads_1.fq'
        fwd_reads_file_path = os.path.join(self.scratch, fwd_reads_file_name)
        shutil.copy(os.path.join('data', fwd_reads_file_name), fwd_reads_file_path)

        rev_reads_file_name = 'reads_2.fq'
        rev_reads_file_path = os.path.join(self.scratch, rev_reads_file_name)
        shutil.copy(os.path.join('data', rev_reads_file_name), rev_reads_file_path)

        reads_object_name = 'test_Reads'
        test_Reads = self.ru.upload_reads({'fwd_file': fwd_reads_file_path,
                                           'rev_file': rev_reads_file_path,
                                           'wsname': self.wsName,
                                           'sequencing_tech': 'Unknown',
                                           'name': reads_object_name
                                           })['obj_ref']

        self.__class__.test_Reads = test_Reads
        print('Loaded Reads: ' + test_Reads)
        return test_Reads

    def loadAssembly(self):
        if hasattr(self.__class__, 'test_Assembly'):
            return self.__class__.test_Assembly

        fasta_file_name = 'test_ref.fa'
        fasta_file_path = os.path.join(self.scratch, fasta_file_name)
        shutil.copy(os.path.join('data', fasta_file_name), fasta_file_path)

        assemlby_name = 'test_Assembly'
        test_Assembly = self.au.save_assembly_from_fasta({'file': {'path': fasta_file_path},
                                                          'workspace_name': self.wsName,
                                                          'assembly_name': assemlby_name
                                                          })

        self.__class__.test_Assembly = test_Assembly
        print('Loaded Assembly: ' + test_Assembly)
        return test_Assembly

    def loadAlignment(self):
        if hasattr(self.__class__, 'test_Alignment'):
            return self.__class__.test_Alignment

        test_Reads = self.loadReads()
        test_Genome = self.loadGenome()

        alignment_file_name = 'accepted_hits.bam'
        alignment_file_path = os.path.join(self.scratch, alignment_file_name)
        shutil.copy(os.path.join('data', alignment_file_name), alignment_file_path)

        alignment_object_name_1 = 'test_Alignment_1'
        destination_ref = self.wsName + '/' + alignment_object_name_1
        test_Alignment = self.rau.upload_alignment({'file_path': alignment_file_path,
                                                    'destination_ref': destination_ref,
                                                    'read_library_ref': test_Reads,
                                                    'condition': 'test_condition_1',
                                                    'library_type': 'single_end',
                                                    'assembly_or_genome_ref': test_Genome
                                                    })['obj_ref']

        self.__class__.test_Alignment = test_Alignment
        return test_Alignment

    def start_test(self):
        testname = inspect.stack()[1][3]
        print('\n*** starting test: ' + testname + ' **')

    def fail_export_to_staging(self, params, error, exception=ValueError, contains=False):
        with self.assertRaises(exception) as context:
            self.getImpl().export_to_staging(self.ctx, params)
        if contains:
            self.assertIn(error, str(context.exception.args))
        else:
            self.assertEqual(error, str(context.exception.args[0]))

    def test_bad_params_export_to_staging_fail(self):
        self.start_test()

        invalidate_params = {'missing_input_ref': 'input_ref',
                             'workspace_name': 'workspace_name'}
        error_msg = '"input_ref" parameter is required, but missing'
        self.fail_export_to_staging(invalidate_params, error_msg)

        invalidate_params = {'input_ref': 'input_ref',
                             'missing_workspace_name': 'workspace_name'}
        error_msg = '"workspace_name" parameter is required, but missing'
        self.fail_export_to_staging(invalidate_params, error_msg)
        
        invalidate_params = {'input_ref': 'input_ref',
                             'workspace_name': 'workspace_name',
                             'missing_destination_dir': 'dd'
        }
        error_msg = '"destination_dir" parameter is required, but missing'
        self.fail_export_to_staging(invalidate_params, error_msg)
        
        invalidate_params = {'input_ref': 'input_ref',
                             'workspace_name': 'workspace_name',
                             'destination_dir': 'safe_dir/../../kbase_secrets_dir'
        }
        error_msg = "destination_dir may not point to an area outside of the user's staging area"
        self.fail_export_to_staging(invalidate_params, error_msg)

    @patch.object(staging_downloader, "STAGING_USER_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_to_staging_reads_ok(self):
        """
        Also tests that the downloaded files have the correct group write permission.
        """
        self.start_test()

        test_Reads = self.loadReads()
        destination_dir = 'test_staging_export'
        params = {'input_ref': test_Reads,
                  'workspace_name': self.wsName,
                  'destination_dir': destination_dir,
                  'generate_report': True}

        ret = self.getImpl().export_to_staging(self.ctx, params)[0]

        reads_files = os.listdir(ret['result_dir'])

        staging_dir = os.path.join('/kb/module/work/tmp/', destination_dir)
        staging_files = os.listdir(staging_dir)
        self.assertTrue(set(staging_files) >= set(reads_files))

        self.assertEqual(len(reads_files), 1)
        reads_file_name = reads_files[0]
        self.assertTrue(reads_file_name.startswith('test_Reads'))
        # self.assertEqual(self.md5(os.path.join(ret['result_dir'], reads_file_name)),
        #                  self.READS_FASTQ_MD5)

        # test that the group write permission is correctly added to the new files
        # and the old permissions are otherwise retained
        self.assertEqual(os.stat(staging_dir).st_mode, 0o040775, staging_dir)
        for f in staging_files:
            self.assertEqual(os.stat(os.path.join(staging_dir, f)).st_mode, 0o100775, f)

    @patch.object(staging_downloader, "STAGING_USER_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_to_staging_assembly_ok(self):
        self.start_test()

        test_Assembly = self.loadAssembly()
        destination_dir = 'test_staging_export'
        params = {'input_ref': test_Assembly,
                  'workspace_name': self.wsName,
                  'destination_dir': destination_dir,
                  'generate_report': True}

        ret = self.getImpl().export_to_staging(self.ctx, params)[0]

        assembly_files = os.listdir(ret['result_dir'])

        staging_files = os.listdir(os.path.join('/kb/module/work/tmp/',
                                                destination_dir))
        self.assertTrue(set(staging_files) >= set(assembly_files))

        self.assertEqual(len(assembly_files), 1)
        assembly_file_name = assembly_files[0]
        self.assertTrue(assembly_file_name.startswith('test_Assembly'))
        self.assertEqual(self.md5(os.path.join(ret['result_dir'], assembly_file_name)),
                         self.ASSEMLBY_FASTA_MD5)

    @patch.object(staging_downloader, "STAGING_USER_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_to_staging_genome_ok(self):
        self.start_test()

        test_Genome = self.loadGenome()
        destination_dir = 'test_staging_export'
        params = {'input_ref': test_Genome,
                  'workspace_name': self.wsName,
                  'destination_dir': destination_dir,
                  'generate_report': True}

        ret = self.getImpl().export_to_staging(self.ctx, params)[0]

        genome_files = os.listdir(ret['result_dir'])

        staging_files = os.listdir(os.path.join('/kb/module/work/tmp/',
                                                destination_dir))
        self.assertTrue(set(staging_files) >= set(genome_files))

        self.assertEqual(len(genome_files), 1)
        genome_file_name = genome_files[0]
        self.assertTrue(genome_file_name.startswith('test_Genome'))
        # self.assertEqual(self.md5(os.path.join(ret['result_dir'], genome_file_name)),
        #                  self.GENOME_GENBANK_MD5)

    def test_export_to_staging_metagenome_ok(self):
        """"""
        self.start_test()
        test_Metagenome = self.loadMetagenome()
        destination_dir = "test_staging_export"
        params = {
            "input_ref": test_Metagenome,
            "workspace_name": self.wsName,
            "destination_dir": destination_dir,
            "generate_report": True
        }
        ret = self.getImpl().export_to_staging(self.ctx, params)[0]
        metagenome_files = os.listdir(ret['result_dir'])
        staging_files = os.listdir(os.path.join('/kb/module/work/tmp/',
                                                self.ctx['user_id'],
                                                destination_dir))
        self.assertTrue(len(set(staging_files)) >= len(set(metagenome_files)))

        self.assertEqual(len(metagenome_files), 4, msg=f"metagenome files {metagenome_files}")

    @patch.object(staging_downloader, "STAGING_GLOBAL_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_to_staging_genome_gff_ok(self):
        self.start_test()

        test_Genome = self.loadGenome()
        destination_dir = 'test_staging_export'
        params = {'input_ref': test_Genome,
                  'workspace_name': self.wsName,
                  'destination_dir': destination_dir + '/../test_staging_export',
                  'generate_report': True,
                  'export_genome': {'export_genome_genbank': 1,
                                    'export_genome_gff': 1}}

        ret = self.getImpl().export_to_staging(self.ctx, params)[0]

        genome_files = os.listdir(ret['result_dir'])

        staging_files = os.listdir(os.path.join('/kb/module/work/tmp/',
                                                self.ctx['user_id'],
                                                destination_dir))
        self.assertTrue(set(staging_files) >= set(genome_files))

        self.assertEqual(len(genome_files), 2)

    @patch.object(staging_downloader, "STAGING_GLOBAL_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_to_staging_alignment_ok(self):
        self.start_test()

        test_Alignment = self.loadAlignment()
        destination_dir = 'test_staging_export'
        params = {'input_ref': test_Alignment,
                  'workspace_name': self.wsName,
                  'destination_dir': destination_dir + "/foo/..",
                  'generate_report': True}

        ret = self.getImpl().export_to_staging(self.ctx, params)[0]

        alignment_files = os.listdir(ret['result_dir'])

        staging_files = os.listdir(os.path.join('/kb/module/work/tmp/',
                                                self.ctx['user_id'],
                                                destination_dir))
        self.assertTrue(set(staging_files) >= set(alignment_files))

        self.assertEqual(len(alignment_files), 2)

        for alignment_file in alignment_files:
            self.assertTrue(alignment_file.startswith('test_Alignment'))
            if alignment_file.endswith('.bam'):
                self.assertEqual(self.md5(os.path.join(ret['result_dir'], alignment_file)),
                                 self.ALIGNMENT_BAM_MD5)

    @patch.object(staging_downloader, "STAGING_GLOBAL_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_to_staging_alignment_sam_ok(self):
        self.start_test()

        test_Alignment = self.loadAlignment()
        destination_dir = 'test_staging_export'
        params = {'input_ref': test_Alignment,
                  'workspace_name': self.wsName,
                  'destination_dir': destination_dir,
                  'generate_report': True,
                  'export_alignment': {'export_alignment_bam': 1,
                                       'export_alignment_sam': 1}}

        ret = self.getImpl().export_to_staging(self.ctx, params)[0]

        alignment_files = os.listdir(ret['result_dir'])

        staging_files = os.listdir(os.path.join('/kb/module/work/tmp/',
                                                self.ctx['user_id'],
                                                destination_dir))
        self.assertTrue(set(staging_files) >= set(alignment_files))

        self.assertEqual(len(alignment_files), 3)

    def fail_export_json_to_staging(self, params, error, exception=ValueError):
        # TODO TEST update to pytest
        with self.assertRaisesRegex(exception, error):
            self.serviceImpl.export_json_to_staging(self.ctx, params)

    def test_export_json_to_staging_fail_bad_params(self):
        self.start_test()

        invalidate_params = {'missing_input_ref': 'input_ref',
                             'destination_dir': 'dd'}
        error_msg = '"input_ref" parameter is required, but missing'
        self.fail_export_json_to_staging(invalidate_params, error_msg)

        invalidate_params = {'input_ref': 'input_ref',
                             'missing_destination_dir': 'dd'}
        error_msg = '"destination_dir" parameter is required, but missing'
        self.fail_export_json_to_staging(invalidate_params, error_msg)
        
        invalidate_params = {'input_ref': 'input_ref',
                             'destination_dir': '../sekrits'}
        error_msg = "destination_dir may not point to an area outside of the user's staging area"
        self.fail_export_json_to_staging(invalidate_params, error_msg)

        invalidate_params = {'input_ref': 'input_ref',
                             'destination_dir': 'ok',
                             'format': "\tfake\t",
        }
        error_msg = 'Unknown format: fake'
        self.fail_export_json_to_staging(invalidate_params, error_msg)

    @patch.object(staging_downloader, "STAGING_USER_FILE_PREFIX", new='/kb/module/work/tmp/')
    def test_export_json_to_staging_standard_format(self):
        self.start_test()
        
        oinfo = self.wsClient.save_objects({"id": self.wsid, "objects": [{
            "name": "json|test",
            "type": "Empty.AType",
            "data": {"sup": "dawg"},
            "meta": {"meta": "data"},
            "provenance": [{"service": "yes, immediately"}],
        }]})[0]
        upa = f"{oinfo[6]}/{oinfo[0]}/{oinfo[4]}"
        filename = "json_test.json"
        
        for format, ddir in [
                (None, "jsonone"),
                ("   \t  ", "jsontwo"),
                ("  standard   ", "jsonthree")
            ]:
            params = {"input_ref": upa, "destination_dir": ddir, "format": format}
            resdir = self.serviceImpl.export_json_to_staging(self.ctx, params)[0]["result_dir"]
            staging_dir = Path("/kb/module/work/tmp/") / ddir
            staging_file = staging_dir / (filename + ".zip")
            rmd5 = self.md5(Path(resdir) / (filename + ".zip"))
            dmd5 = self.md5(staging_file)
            assert rmd5 == dmd5
            with zipfile.ZipFile(staging_file) as z:
                assert z.namelist() == [filename]
                with z.open(filename) as f:
                    js = json.loads(f.read())
                    assert js["info"][2].split("-")[0] == "Empty.AType"
                    js["info"][2] = None
                    js["info"][3] = None  # drop time
                    js["created"] = None
                    js["epoch"] = None
                    expected = {
                        "data": {"sup": "dawg"},
                        "info": [
                            1,
                            "json|test",
                            None,
                            None,
                            1,
                            self.ctx["user_id"],
                            self.wsid,
                            self.wsName,
                            "8e041a86b7267bc9e0fc624786b5bc49",
                            14,
                            {"meta": "data"},
                        ],
                        "path": [str(self.wsid) + "/1/1"],
                        "provenance": [
                            {
                                "service": "yes, immediately",
                                "method_params": [],
                                "input_ws_objects": [],
                                "resolved_ws_objects": [],
                                "intermediate_incoming": [],
                                "intermediate_outgoing": [],
                                "external_data": [],
                                "subactions": [],
                                "custom": {}
                            }
                        ],
                        "creator": self.ctx["user_id"],
                        "orig_wsid": self.wsid,
                        "created": None,
                        "epoch": None,
                        "refs": [],
                        "copy_source_inaccessible": 0,
                        "extracted_ids": {}
                    }
                    # TODO this would be a whole lot easier to debug with pytest
                    assert js == expected
            # test that the group write permission is correctly added to the new files
            # and the old permissions are otherwise retained
            assert os.stat(staging_dir).st_mode == 0o040775
            assert os.stat(staging_file).st_mode == 0o100775
