package Data::Babel::Formatter;
use strict;
use warnings;


sub get_mimetype {
    my ($format)=@_;
    $format ||= 'unknown';

    # set content (mime) type:
    my $mimetype={html=>'text/html',
		  xml=>'text/plain',
		  json=>'application/json',
		  csv=>'text/plain',
		  tsv=>'text/plain',
		  unknown=>'text/plain'}->{$format}; 
}


sub format_table {
    my ($table,$format)=@_;
    my $formatter="as_$format";
    no strict "refs";
    my $content=&$formatter($table);
    use strict "refs";
    $content;
}

sub as_html {
    my ($translations)=@_;
    my $output_display_names=output_display_names();
    my $html=array2d_as_html_table(data=>$translations, col_names=>$output_display_names);
}

sub as_csv {
    my ($translations)=@_;
    my $header='#'.join(",",output_display_names());
    array2d_as_table(data=>$translations, header=>"$header\n", row_sep=>",");
}

sub as_tsv {
    my ($translations)=@_;
    my $header='#'.join("\t",output_display_names());
    array2d_as_table(data=>$translations, header=>"$header\n", row_sep=>"\t");
}

sub as_json {
    my ($translations)=@_;
    my $json=encode_json($translations);
}

# Not using this
# sub as_r {
#     my ($translations)=@_;
#     my $header=join("\n",output_display_names());
#     array2d_as_table(data=>$translations, header=>"$header\n", row_sep=>"\t");
# }

sub as_xml {
    my ($translations)=@_;
    my $input_type=$request{input_type};
    my $output_types=$request{output_types};
    my @input_ids=$request{input_ids};

    my $hashlist;
    foreach my $t (@$translations) {
	my $input_id=shift @$t;
	if (scalar @$t != scalar @$output_types) { # fixme: catch this exception
	    die(sprintf "bad row size %d vs %d", scalar @$t, (scalar @$output_types)+1);
	}
	my %hash;
	@hash{@$output_types}=@$t;
	push @$hashlist,{output_ids=>\%hash, input_id=>$input_id};
    }
    
    my $p=new XML::Simple(ForceArray=>[qw(translation)], KeyAttr=>{}, NoAttr=>1, RootName=>'Babel');
    $p->XMLout({translations=>{translation=>$hashlist}});
}
