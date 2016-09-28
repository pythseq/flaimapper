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


import os,re,random,operator,argparse,sys
import pysam

import flaimapper


class FragmentContainer():
    def __init__(self,verbosity):
        self.verbosity = verbosity
        
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
    
    def export_genbank(self,filenamePrefix,suffixes=['_grouped.gbk','_single.gbk'],loffset = -3,roffset = 5):
        """Write discovered fragments to genbank format (2 files). Certain arguments are created arbitrary just to make them non-empty.
        
        The following files:
        - *grouped: 
        - *single: 
        
        ----
        @param filenamePrefix:
        @param suffixes:
        @param loffset:
        @param roffset:
        
        @return: Success of the function
        @rtype: boolean
        """
        if(not self.sequences):
            return False
        else:
            if(filenamePrefix == "-"):
                print "Currently stdout is not supported for genbank"
            
            fh_grouped = open(filenamePrefix+suffixes[0],'w')
            fh_single = open(filenamePrefix+suffixes[1],'w')
            
            for name in sorted(self.sequences.keys()):
                for masked_region_id in sorted(self.sequences[name]):
                    result = self.sequences[name][masked_region_id].results
                    if(result):
                        preSeq = self.sequences[name].seq
                        fh_grouped.write('LOCUS	   '+name+'		'+str(len(preSeq))+' bp	DNA	 linear   UNA'+"\n"+'DEFINITION  Homo sapiens '+name[0:150]+' ncRNA\n'+'ACCESSION   '+name+"\n"+'SOURCE	  Homo sapiens'+"\n"+'REFERENCE   1  '+"\n"+'  AUTHORS   ???;'+"\n"+'  TITLE	 \"A certain title\"'+"\n"+'  JOURNAL   ??? ???'+'\n   PUBMED   12345678'+"\nFEATURES			 Location/Qualifiers"+"\n")
                        
                        j = 1
                        for fragment in result:
                            fh_single.write('LOCUS	   '+name+'_Fragment_'+str(j)+'		'+str(len(fragment['extended']['sequence']))+' bp	DNA	 linear   UNA'+"\n"+'DEFINITION  Homo sapiens '+name[0:150]+' ncRNA\n'+'ACCESSION   '+name+'_Fragment_'+str(j)+"\n"+'SOURCE	  Homo sapiens'+"\n"+'REFERENCE   1  '+"\n"+'  AUTHORS   Person X;'+"\n"+'  TITLE	 \"A certain title\"'+"\n"+'  JOURNAL   JournalX. 5:e1000123(2012.'+'\n   PUBMED   12345678'+"\nFEATURES			 Location/Qualifiers"+"\n")
                            fh_single.write("	 Fragment		"+str(fragment['extended']['5_prime_cut']+1)+".."+str(len(fragment['extended']['sequence'])-fragment['extended']['3_prime_cut'])+"\n")
                            fh_single.write("					 /accession=mir-"+name+'_Fragment_'+str(j)+"\n")
                            fh_single.write("					 /product=mir-"+name+'_Fragment_'+str(j)+"\n")
                            fh_single.write("					 /evidence=experimental"+"\n")
                            fh_single.write("					 /experiment=\"Solexa\""+"\n")
                            fh_single.write("ORIGIN\n"+self.writeGenBank__format_sequence(fragment['extended']['sequence'])+"//"+"\n")
                            
                            fh_grouped.write("	 Fragment		"+str((int(fragment['start'])+1))+".."+str((int(fragment['stop'])))+"\n")
                            fh_grouped.write("					 /accession="+name+'_Fragment_'+str(j)+"\n")
                            fh_grouped.write("					 /product="+name+'_Fragment_'+str(j)+"\n")
                            fh_grouped.write("					 /evidence=experimental"+"\n")
                            fh_grouped.write("					 /experiment=\"Solexa\""+"\n")
                            j += 1
                        
                        fh_grouped.write("ORIGIN\n"+self.writeGenBank__format_sequence(preSeq)+"//"+"\n")
            
            fh_single.close()
            fh_grouped.close()
            
            return True
    
    def export_genbank__format_sequence(self,seq,size=60):
        """Formats a sequence in order to use it for GenBank files.
        Sequences get broken up in slices of 'size' which is 60
        nucleotides by default.
        
        ----
        @param seq: The DNA sequence
        @param size: The length in amino acids that one row may take.
        
        @return: Tidy formatted DNA string
        @rtype: string
        """
        outp = ''
        times = ((len(seq) - len(seq)%size) / size)
        for i in range(times+1):
            slice = seq[i*size:(i+1)*size]
            outp += "		 "[len(str((i*size)+1)):]+str((i*size)+1)+" "+slice+"\n"
        return outp
    
    def export_table__per_ncRNA(self,filename):
        """Writes the discovered framents to a tab-delimited file.
        
        ----
        @param filename: the desired filename
        
        @return: success
        @rtype: boolean
        """
        if(not self.sequences):
            return False												# Raise error?
        else:
            if(filename == "-"):
                fh = sys.stdout
            else:
                fh = open(filename,'w')
            
            fh.write("NAME\tCurated\tUnreliable")
            
            for i in range(0,25):
                letter = chr(ord('A')+i)
                fh.write("\tFragment-"+letter+"-Start\tFragment-"+letter+"-Stop\tFragment-"+letter+"-Sequence")
            
            fh.write("\n")
            
            for name in sorted(self.sequences.keys()):
                for masked_region_id in sorted(self.sequences[name]):
                    result = self.sequences[name][masked_region_id].results
                    if(result):
                        row = name+"\tNo\t?"
                        
                        for fragment in result:
                            row += "\t"+str(fragment['start'])+"\t"+str(fragment['stop'])+"\t"+str(fragment['sequence'])
                        
                        fh.write(row+"\n")
        
        fh.close
        return True
    
    def export_table__per_fragment(self,filename):
        """Exports the discovered fragments to a tab-delimited file.
        
        The following format is exported:
        
        ----
        @param filename The target file.
        
        @return:
        @rtype:
        """
        if(not self.sequences):
            print "     * Warning: no fragments detected"
        else:
            if(filename == "-"):
                fh = sys.stdout
            else:
                fh = open(filename,'w')
            
            
            if(self.fasta_file):
                fh.write("Fragment\tSize\tReference sequence\tStart\tEnd\tPrecursor\tStart in precursor\tEnd in precursor\tSequence (no fasta file given)\tCorresponding-reads (start)\tCorresponding-reads (end)\tCorresponding-reads (total)\n")
            else:
                fh.write("Fragment\tSize\tReference sequence\tStart\tEnd\tPrecursor\tStart in precursor\tEnd in precursor\tSequence\tCorresponding-reads (start)\tCorresponding-reads (end)\tCorresponding-reads (total)\n")
            
#            for name in sorted(self.sequences.keys()):
#                for masked_region_id in sorted(self.sequences[name]):
#                    result = self.sequences[name][masked_region_id].results
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
        if(self.verbosity == "verbose"):
            print " - Exporting results to: "+output_filename
        if(export_format == 1):
            print "   - Format: tab-delimited, per fragment"
            self.export_table__per_fragment(output_filename)
        elif(export_format == 2):
            print "   - Format: tab-delimited, per ncRNA"
            self.export_table__per_ncRNA(output_filename)
        elif(export_format == 3):
            print "   - Format: gen-bank"
            self.export_genbank(output_filename)
        elif(export_format == 4):
            print "   - Format: GTF"
            self.export_gtf(output_filename)
