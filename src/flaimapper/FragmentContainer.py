#!/usr/bin/env python

"""FlaiMapper: computational annotation of small ncRNA derived fragments using RNA-seq high throughput data

 Here we present Fragment Location Annotation Identification mapper
 (FlaiMapper), a method that extracts and annotates the locations of
 sncRNA-derived RNAs (sncdRNAs). These sncdRNAs are often detected in
 sequencing data and observed as fragments of their  precursor sncRNA.
 Using small RNA-seq read alignments, FlaiMapper is able to annotate
 fragments primarily by peak-detection on the start and  end position
 densities followed by filtering and a reconstruction processes.
 Copyright (C) 2011-2014:
 - Youri Hoogstrate
 - Elena S. Martens-Uzunova
 - Guido Jenster
 
 
 [License: GPL3]
 
 This file is part of flaimapper.
 
 flaimapper is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 flaimapper is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program. If not, see <http://www.gnu.org/licenses/>.

 Documentation as defined by:
 <http://epydoc.sourceforge.net/manual-fields.html#fields-synonyms>
"""


import os,re,random,operator,argparse,sys,logging
import pysam

import flaimapper


class FragmentContainer():
    def add_fragments(self,fragment_finder_results,fasta_file=None):
        """
        
        ----
        @param fragment_finder_results: 
        """
        
        #for fragment in fragment_finder_results.results:
        uid = fragment_finder_results.masked_region[0]+"_"+str(fragment_finder_results.masked_region[1])+"_"+str(fragment_finder_results.masked_region[2])
        if(uid not in self.sequences.keys()):
            self.sequences[uid] = []
        
        self.sequences[uid].append(fragment_finder_results)
        self.fasta_file = fasta_file
    
    def export_table__per_fragment(self,filename):
        """Exports the discovered fragments to a tab-delimited file.
        
        The following format is exported:
        
        ----
        @param filename The target file.
        
        @return:
        @rtype:
        """
        if(not self.sequences):
            logging.warning("     * Warning: no fragments detected")
        else:
            if(filename == "-"):
                fh = sys.stdout
            else:
                fh = open(filename,'w')
            
            
            if(self.fasta_file):
                fh.write("Fragment\tSize\tReference sequence\tStart\tEnd\tPrecursor\tStart in precursor\tEnd in precursor\tSequence (no fasta file given)\tCorresponding-reads (start)\tCorresponding-reads (end)\tCorresponding-reads (total)\n")
            else:
                fh.write("Fragment\tSize\tReference sequence\tStart\tEnd\tPrecursor\tStart in precursor\tEnd in precursor\tSequence\tCorresponding-reads (start)\tCorresponding-reads (end)\tCorresponding-reads (total)\n")
            
            for uid in sorted(self.sequences.keys()):
                for reference_sequence in self.sequences[uid]:
                    name = reference_sequence.masked_region[0]
                    result = reference_sequence.results
                    if(result):
                        fragments_sorted_keys = {}
                        for fragment in result:
                            fragments_sorted_keys[fragment['start']] = fragment
                        
                        i = 0
                        for key in sorted(fragments_sorted_keys.keys()):	# Walk over i in the for-loop:
                            i += 1
                            fragment = fragments_sorted_keys[key]
                            
                            # Fragment uid
                            fh.write('FM_'+ name+'_'+str(i).zfill(12)+"\t")
                            
                            # Size
                            fh.write(str(fragment['stop'] - fragment['start'] + 1) + "\t")
                            
                            # Reference sequence 
                            fh.write(name + "\t")
                            
                            # Start
                            fh.write(str(fragment['start']) + "\t")
                            
                            # End
                            fh.write(str(fragment['stop'])+"\t")
                            
                            # Precursor
                            fh.write(fragment.masked_region[0])
                            
                            # Start in precursor
                            fh.write("\t" + str(fragment['start']-fragment.masked_region[1])+ "\t")
                            
                            # End in precursor
                            fh.write(str(fragment['stop']-fragment.masked_region[1])+"\t")
                            
                            # Sequence 
                            if(self.fasta_file):
                                # PySam 0.8.2 claims to use 0-based coordinates pysam.FastaFile.fetch().
                                # This is only true for the start position, the end-position is 1-based.
                                fh.write(str(self.fasta_file.fetch(name,fragment['start'],fragment['stop']+1)))
                            
                            # Start supporting reads
                            fh.write("\t"+str(fragment['start_supporting_reads'])+"\t")
                            
                            # Stop supporting reads
                            fh.write(str(fragment['stop_supporting_reads'])+"\t")
                            
                            # Total supporting reads
                            fh.write(str(fragment['stop_supporting_reads']+fragment['start_supporting_reads']) + "\n")
            
            fh.close()
        
    def export_gtf(self,filename):
        if(filename == "-"):
            fh = sys.stdout
        else:
            fh = open(filename,'w')
        
        for uid in sorted(self.sequences.keys()):
            for reference_sequence in self.sequences[uid]:
                name = reference_sequence.masked_region[0]
                result = reference_sequence.results
                
                if(result):
                    fragments_sorted_keys = {}
                    for fragment in result:
                        fragments_sorted_keys[fragment['start']] = fragment
                    
                    i = 0
                    for key in sorted(fragments_sorted_keys.keys()):# Walk over i in the for-loop:
                        i += 1
                        fragment = fragments_sorted_keys[key]
                        
                        # Seq-name
                        fh.write(name + "\t")
                        
                        # Source
                        fh.write("flaimapper-v"+flaimapper.__version__+"\t")
                        
                        # Feature
                        fh.write("sncdRNA\t")
                        
                        # Start
                        fh.write(str(fragment['start']+1) + "\t")
                        
                        # End
                        fh.write(str(fragment['stop']+1)+"\t")
                        
                        # Score
                        fh.write(str(fragment['stop_supporting_reads']+fragment['start_supporting_reads']) + "\t")
                        
                        # Strand and Frame
                        fh.write(".\t.\t")
                        
                        # Attribute
                        attributes = []
                        attributes.append('gene_id "FM_'+ name+'_'+str(i).zfill(12)+'"' )
                        
                        fh.write(", ".join(attributes)+"\n")
        fh.close()
    
    def write(self,export_format,output_filename):
        logging.debug(" - Exporting results to: "+output_filename)
        
        if(export_format == 1):
            logging.info("   - Format: tab-delimited, per fragment")
            self.export_table__per_fragment(output_filename)
        elif(export_format == 2):
            logging.info("   - Format: GTF")
            self.export_gtf(output_filename)
