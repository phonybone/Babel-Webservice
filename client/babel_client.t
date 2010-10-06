#!/usr/bin/env perl 
# -*-perl-*-

use strict;
use warnings;
use Carp;
use Data::Dumper;
use Test::More;
use FindBin;
use lib "$FindBin::Bin/..";

use lib '/home/victor/sandbox/perl/PhonyBone';
use Options;

use vars(qw($class));
$class='BabelClient';
confess "class not initiated" unless defined $class;


BEGIN: {
  Options::use(qw(d h));
    Options::useDefaults(fuse => -1);
    Options::get();
    die Options::usage() if $options{h};
    $ENV{DEBUG} = 1 if $options{d};
}


sub main {
    require_ok($class) or die "failed require_ok($class); aborting\n";

    my $bc=new BabelClient;
#    test_idtypes($bc) or goto DONE;
    test_translate($bc) or goto DONE;

  DONE:
    done_testing();
}


our %idtypes_expected=('transcript_ensembl'=>  'Ensembl transcript id',
	      'protein_refseq'=> 'RefSeq protein id',
	      'probe_nu'=> 'nucleotide universal id',
	      'probe_lumi'=> 'Illumina probe id',
	      'function_omim'=> 'OMIM number',
	      'chip_lumi'=> 'Illumina array',
	      'gene_unigene'=> 'UniGene id',
	      'transcript_ncbi'=> 'GenBank transcript id',
	      'gene_symbol'=> 'gene symbol',
	      'protein_ncbi'=> 'NCBI protein id',
	      'gene_known'=> 'UCSC known gene id',
	      'organism_name_common'=> 'organism',
	      'transcript_refseq'=> 'RefSeq transcript id',
	      'protein_uniprot'=> 'UniProt id',
	      'chip_affy'=> 'Affymetrix array',
	      'probe_affy'=> 'Affymetrix probeset id',
	      'gene_description'=> 'gene description',
	      'sequence_affy'=> 'Affymetrix probeset sequence',
	      'gene_entrez'=> 'Entrez gene id',
	      'function_omim_description'=> 'OMIM description',
	      'protein_ensembl'=> 'Ensembl protein id',
	      'protein_ipi_description'=> 'IPI protein description',
	      'transcript_epcondb'=> 'EpconDB transcript id',
	      'sequence_nu'=> 'nucleotide universal id sequence',
	      'reaction_ec'=> 'EC number',
	      'peptide_pepatlas'=> 'Peptide Atlas id',
	      'function_go'=> 'GO id',
	      'protein_ipi'=> 'IPI id',
	      'gene_symbol_synonym'=> 'gene synonym',
	      'gene_ensembl'=> 'Ensembl gene id');

sub test_idtypes {
    my ($bc)=@_;
    my @idtypes=$bc->idtypes;
    my %idtypes=map {($_->[0],$_->[1])} @idtypes;
    
    my $ok=1;
    while (my ($k,$v)=each %idtypes) {
	if (!ok(exists($idtypes_expected{$k}),"found $k")) {
	    $ok=0;
	    next;
	}
	if (!is($idtypes_expected{$k},$idtypes{$k},"$k matches '$v'")) {
	    $ok=0;
	    next;
	}
    }
    warn "test_idtypes returning $ok\n";
    $ok;
}

sub test_translate {
    my ($bc)=@_;
    my %args=(input_type=>'gene_entrez',
	      input_ids=>[2983,1829,589,20383,293883],
	      output_types=>[qw(protein_ensembl peptide_pepatlas reaction_ec function_go gene_symbol_synonym)],
	      output_format=>'json');
    my $table=$bc->translate(%args);
    warn "table is ",Dumper($table);
	      
}

sub test_bad_translate_request {
}

main();
