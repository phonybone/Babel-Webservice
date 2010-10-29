#!/jdrf_tools/bin/perl
# -*-perl-*-

# Implement a simple web service that serves Babel translations between biological 
# identifiers (eg entrez gene, uniprot ids, etc).

# Todo: 
# Implement better defaults for inputs, possibly via get_param() (currently defaults
# for some parameters are scattered amongst the code.
# Cleanup any instances of request-specific data; anywhere code such as "if $request_type eq 'translate'"
# or similar appears should be consolidated and made scalable.

use strict;
use warnings;
use Carp;
use FindBin;
use DBI;
use Data::Dumper;
use Log::Handler;
use CGI;
use JSON;

use lib '/home/vcassen/sandbox/perl/lib/lib/perl5';
use Data::Babel;
use Data::Babel::Config;
use Class::AutoDB;

our $is_webpage=defined $ENV{DOCUMENT_ROOT};
our (%conf,$dbh,$babel,$cgi,$logger);
require 'translate.conf';

$logger=new Log::Handler();
$logger->add(file=>$conf{logfile});

if ($is_webpage) {
    $SIG{__WARN__}=sub { $logger->debug(@_) };
    $cgi= new CGI;
} else {
    open (CGIINPUT,$conf{cgi_input}) or die "Can't open $conf{cgi_input}: $!\n";
    $cgi=new CGI(*CGIINPUT);
    close CGIINPUT;
}

our @request_methods=qw(translate idtypes request_form);
our %formats=(HTML=>'html', XML=>'xml', JSON=>'json', 'Comma separated'=>'cvs', 'Tab separated'=>'tsv', R=>'r');
our %defaults=(output_format=>'html',
	       request_type=>'request_form');

sub main {
    my $content;
    eval {
	my $method=get_param('request_type', 'request_form');
	die "unknown request '$method'\n" unless grep /^$method$/, @request_methods;

        # all request methods must return a two-element array containing headers (HASHREF) and content (SCALAR):
	init_dbs();
	no strict "refs";
	$content=&$method();
	use strict "refs";
    };


    if ($@) {			# gots to be really careful: nothing in this block can throw an exception!
	my $error=$@;
	warn "exception: $error\n";
	$error=~s/\n$//;

	my $format;
	if ($error=~/unknown format/) {
	    $format='html';	# have to choose something
	} else {
	    $format=$cgi->param('output_format') || 'html'; # likewise
	}
	my $error_method="error_as_$format";
	no strict "refs";
	$content=&$error_method($error);
	use strict "refs";
    }
    my $mimetype=get_mimetype();
    my $headers={'Content-type'=>$mimetype};
    print final_output($headers,$content);
}

sub final_output {
    my ($headers,$content)=@_;

    my $content_type=$headers->{'Content-type'} || 'text/plain';
    my $output="Content-type: $content_type\r\n";
    delete $headers->{'Content-type'};
    $output.=join("\r\n",map { "$_: ".$headers->{$_} } keys %$headers);
    $output.="\r\n";
    $output.=$content;
}

sub init_dbs {
    our $autodb=new Class::AutoDB(%{$conf{autodb}});

    # try to get existing Babel from database
    $babel=old Data::Babel(name=>$conf{autodb}->{name},autodb=>$autodb);

    unless ($babel) {
	# Babel does not yet exist, so we'll create it

	# first, create component objects from configuration files
	my $idtypes=new Data::Babel::Config(filename=>'conf/idtype.ini')->objects;
	my $masters=new Data::Babel::Config(filename=>'conf/master.ini')->objects;
	my $maptables=new Data::Babel::Config(filename=>'conf/maptable.ini')->objects;

	# now we can create the Babel
	$babel=new Data::Babel
	    (name=>$conf{autodb}->{database},idtypes=>$idtypes,masters=>$masters,maptables=>$maptables);
    }


# open database containing real data
    $dbh=DBI->connect("dbi:mysql:database=$conf{autodb}->{database}",$conf{autodb}->{user},$conf{autodb}->{password}) or
	die "error connection to db: $DBI::errstr";
}

sub request_form {
    use Template;
    my $tt=Template->new(INCLUDE_PATH=>"$FindBin::Bin/../htdocs",
				  );
    my $id_types_array=[sort {lc $a->[1] cmp lc $b->[1]} map {[$_->name, $_->display_name]}  @{$babel->idtypes}];
    my $vars={id_type_options=>array2d_as_options($id_types_array),
	      output_type_cbs=>array2d_as_checkboxes(arrayref=>$id_types_array, name=>'output_types',separator=>"<br />\n"),
	      output_format_options=>hash_as_options(\%formats),
	  };


    my $content;
    $tt->process("request_form.tt",$vars,\$content);
    ({"Content-type"=>'text/html'},$content);
}

########################################################################

# translate a set of input_ids 
# required cgi params: qw(input_type, input_ids, output_types, output_format
# 
sub translate {
    my $output_types=[$cgi->param('output_types')];
    if (@$output_types==1) {
	my @l=split(/[,\s]/,$output_types->[0]);
	$output_types=\@l if @l>1;
    }
    my $input_ids=[split(/[\s,]/,get_param('input_ids'))];
    my %args=(dbh=>$dbh,
	      input_idtype=>get_param('input_type'),
	      input_ids=>$input_ids,
	      output_idtypes=>$output_types,
	      return_type=>'array',
	      );
    my $table;
    eval { $table=$babel->translate(%args) };
    die confession2die($@) if $@;

    my $content=format_table($table);
}

sub idtypes {
    my $table=[map {[$_->name,$_->display_name]} @{$babel->idtypes}];
    my $content=format_table($table);
}

########################################################################

sub format_table {
    my ($table)=@_;
    my $format=$cgi->param('output_format') ||  'html';
    my $formatter="as_$format";
    no strict "refs";
    my $content=&$formatter($table);
    use strict "refs";
    $content;
}

sub get_mimetype {
    my $format=$cgi->param('output_format') || 'html';
    # set content (mime) type:
    my $mimetype={html=>'text/html',
		  xml=>'text/xml',
		  json=>'text/x-json',
		  csv=>'text/plain',
		  tsv=>'text/plain'}->{$format} || 'text/plain'; # handle unknown format error elsewhere
}

########################################################################

sub hash_as_options {
    my ($hashref, $sorter)=@_;
    $sorter = sub { $_[0] cmp $_[1] } unless ref $sorter eq 'CODE';
    join("\n",map {"<option value='$hashref->{$_}'>$_</option>\n"} sort $sorter keys %$hashref);
    
}

sub array_as_options {
    my ($arrayref)=@_;
    join("\n",map "<option value='$_'>$_</option>", @$arrayref)
}

sub array2d_as_options {
    my ($arrayref)=@_;
    join("\n",map "<option value='$_->[0]'>$_->[1]</option>", @$arrayref)
}

sub array2d_as_checkboxes {
    my (%argHash)=@_;
    my ($arrayref,$separator,$name,$checked)=@argHash{qw(arrayref separator name checked)};
    my $checked_str=defined $checked? "checked='1'" : '';
    join($separator,map "<input type='checkbox' name='$name' value='$_->[0]' $checked_str />$_->[1]", @$arrayref);
}

sub array2d_as_table {
    my %argHash=@_;
    my %defaults=(header=>'', footer=>'', row_header=>'', row_footer=>"\n", row_sep=>' ');
    while (my ($k,$v)=each %defaults) { $argHash{$k}=$v unless exists $argHash{$k} }
    my ($data,$header,$footer,$row_header,$row_footer,$row_sep)=
	@argHash{qw(data header footer row_header row_footer row_sep)};
    
    my $table=$header;
    foreach my $row (@$data) {
	@$row=map{defined $_? $_:''} @$row;
	my $tds=join($row_sep,@$row);
	$table.=join('',$row_header,$tds,$row_footer);
    }
    $table.=$footer;
}

sub array2d_as_html_table {
    my %argHash=@_;
    my $header="<table";

    if (my $attrs=$argHash{attrs}) {
	while (my ($k,$v)=each %$attrs) {
	    $header.=" $k='$v'";
	}
    }
    $header.=">\n";		# close off <table> tag

    if (ref $argHash{col_names} eq 'ARRAY') {
	$header.="<tr><th>";
	$header.=join('</th><th>',@{$argHash{col_names}});
	$header.="</th></tr>\n";
    }
    array2d_as_table(data=>$argHash{data},col_names=>$argHash{col_names},
		     header=>$header,footer=>"</table>\n",row_header=>"<tr><td>",row_footer=>"</td></tr>\n",row_sep=>"</td>\n<td>");
}

########################################################################

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

sub as_r {
    my ($translations)=@_;
    my $header=join("\n",output_display_names());
    array2d_as_table(data=>$translations, header=>"$header\n", row_sep=>"\t");
}

sub as_xml {
    my ($translations)=@_;

    my $tag=$cgi->param('request_type');
    my ($input_type,@output_types);
    if ($tag eq 'translate') {
	$input_type=$cgi->param('input_type');
	@output_types=grep {$_ ne $input_type} $cgi->param('output_types');
    } elsif ($tag eq 'idtypes') {
	$tag='idtype';		# remove an extra 's'; makes output prettier
	$input_type='name';
	@output_types=qw(display_name);
    } else {
	die "unknown request type '$tag'"; # not really true; could be 'request_form', but then this makes no sense
    }

    my $xml="<xml>\n  <${tag}s>\n";
    foreach my $row (@$translations) {
	$xml.="    <$tag>\n";
	my $input_id=shift @$row;
	$xml.="      <$input_type>$input_id</$input_type>\n";
	foreach my $ot (@output_types) {
	    $xml.="      <$ot>".(shift @$row)."</$ot>\n";
	}
	$xml.="    </${tag}>\n";
    }
    $xml.="  </${tag}s>\n</xml>\n";
}

# return an array(ref) of display names for the output types
# display names
sub output_display_names {
    my $request_type=$cgi->param('request_type');
    my @display_names;
    if ($request_type eq 'translate') {
	my %name2displayname=map {($_->name,$_->display_name)} @{$babel->idtypes};
	@display_names=map {$name2displayname{$_}} grep {$_ ne $cgi->param('input_type')} $cgi->param('output_types');
	unshift @display_names,$name2displayname{$cgi->param('input_type')};
    } elsif ($request_type eq 'idtypes') {
	@display_names=qw(name display_name);
    } else {
	die "unknown request_type '$request_type'";
    }
    wantarray? @display_names:\@display_names;
}

########################################################################

sub error_as_csv {
    my ($error)=@_;
    "$error\n";
}

sub error_as_tsv {
    my ($error)=@_;
    "$error\n";
}

# actually return plaintext (for now)
sub error_as_html {
    my ($error)=@_;
    "$error;\n"
}

sub error_as_xml {
    my ($error)=@_;
    "<xml><error>$error</error></xml>\n";
}

sub error_as_json {
    my ($error)=@_;
    encode_json({error=>$error});
}

sub error_as_r {
    my ($error)=@_;
    "$error;\n";
}

sub confession2die {
    local $@=shift;
    $@=(split(/\n/,$@))[0];
    $@=~s| at \/.*||;
    $@=~s| at translate.cgi.*||;
    "$@\n";
}

########################################################################

# Can't use this on things that return a list value (checkboxes, multi-selects, etc)
sub get_param {
    my ($name,$default)=@_;
    my $value=$cgi->param($name);
    $value=$default if !$value && defined $default; # $value will be defined if it exists in the form but is not supplied
    
    die "missing parameter '$name'\n" unless $value;
    $value;
}

main();
