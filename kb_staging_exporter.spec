/*
A KBase module: kb_staging_exporter
*/

module kb_staging_exporter {

  /* Ref to a WS object
      @id ws
  */
  typedef string WSRef;

  /* workspace name of the object
  */
  typedef string workspace_name;

  /* Input of the export_to_staging function
    input_ref: workspace object reference
    workspace_name: workspace name objects to be saved to 
    destination_dir: destination directory for downloaded files

    optional:
    generate_report: indicator for generating workspace report. (default False)
    export_genome: indicator for downloading Genbank (setting export_genome_genbank: 1) 
                                          or GFF (setting export_genome_gff: 1). (default download Genbank)
    export_alignment: indicator for downloading BAM (setting export_alignment_bam: 1) 
                                             or SAM (setting export_alignment_sam: 1). (default download BAM)
  */
  typedef structure {
    WSRef input_ref;
    workspace_name workspace_name;
    string destination_dir;
    string generate_report;
    mapping<string, string> export_genome;
    mapping<string, string> export_alignment;
  } ExportStagingParams;

  typedef structure {
      string report_name;
      string report_ref;
      string result_dir;
  } ExportStagingOutput;

  /* export_to_staging: export large file associated with workspace object to staging area*/
  funcdef export_to_staging (ExportStagingParams params) returns (ExportStagingOutput returnVal) authentication required;

};
