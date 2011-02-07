#!/jdrf_tools/bin/perl
# -*-perl-*-

# Implement a simple web service that serves Babel translations between biological 
# identifiers (eg entrez gene, uniprot ids, etc).

# Todo: 
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
use Text::CSV;
use XML::Simple qw(:strict);

use lib "$FindBin::Bin/../lib";
use Data::Babel::IO;

use Data::Babel;
use Data::Babel::Config;
use Class::AutoDB;

our (%conf,$babel,$cgi,$logger,$io);
require "$FindBin::Bin/translate.conf";	# defines %conf

our $is_webpage= defined $ENV{DOCUMENT_ROOT}; 
if ($conf{logfile}) {
    my $logfile=$conf{logfile}->{filename};
    $logger=new Log::Handler();
    $logger->add(file=>$conf{logfile});
    chmod $conf{logfile}->{permissions}, $logfile if $conf{logfile}->{permissions};
    if ($is_webpage) {
#	$SIG{__WARN__}=sub { $logger->debug(@_) };
    }
}

our @request_methods=qw(translate idtypes request_form input_ids_all);
our %defaults=(output_format=>'html',
	       request_type=>'request_form');

sub main {
    my ($mimetype,$content);

    eval {
	$babel=init_babel();
	$io=Data::Babel::IO->new(idtypes=>$babel->idtypes, is_webpage=>$is_webpage); # gets request

	my $method=$io->request->{request_type};
	die "unknown request '$method'\n" unless grep /^$method$/, @request_methods;
	$mimetype=$io->get_mimetype();

        # all request methods must return a two-element array containing headers (HASHREF) and content (SCALAR):
	no strict "refs";
	$content=&$method();
	use strict "refs";
    };

    if ($@) {			# gots to be really careful: nothing in this block can throw an exception!
	my $error=$@;
#	warn $error;
	$error=~s/\n$//;

	my $format;
	if ($error=~/Unknown output format/ || ref $io ne 'Data::Babel::IO') {
	    $format='json';	# have to choose something
	} else {
	    $format=$io->request->{output_format} || 'json'; # likewise
	}
	my $error_method="error_as_$format";
	no strict "refs";
	$content=&$error_method($error);
	use strict "refs";
    }

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

sub init_babel {
    my $autodb=new Class::AutoDB(%{$conf{autodb}});

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
    confess "unable to create babel object" unless ref $babel eq 'Data::Babel';
    $babel;
}

########################################################################

sub request_form {
    use Template;
    my $tt=Template->new(INCLUDE_PATH=>"$FindBin::Bin/../htdocs",
			 );
    my $id_types_array=[sort {lc $a->[1] cmp lc $b->[1]} map {[$_->name, $_->display_name]}  @{$babel->idtypes}];
    my $vars={id_type_options=>array2d_as_options($id_types_array),
	      output_type_cbs=>array2d_as_checkboxes(arrayref=>$id_types_array, name=>'output_types',separator=>"<br />\n"),
	      output_format_options=>hash_as_options($io->formats),
	      server=>$ENV{SERVER_NAME},
	  };
    
    
    my $content;
    $tt->process("request_form.tt",$vars,\$content);
    ({"Content-type"=>'text/html'},$content);
}


# translate a set of input_ids 
# required cgi params: qw(input_type, input_ids, output_types, output_format
# 
sub translate {
    my $output_types=$io->request->{output_types};
    my $input_ids=$io->request->{input_ids};
    my $input_type=$io->request->{input_type};
    my $input_ids_all=$io->request->{input_ids_all};

    # open database containing real data
    my $dbh=DBI->connect("dbi:mysql:database=$conf{autodb}->{database}",$conf{autodb}->{user},$conf{autodb}->{password}) or
	die "error connection to db: $DBI::errstr";

    my %args=(dbh=>$dbh,
	      input_idtype=>$input_type,
	      output_idtypes=>$output_types,
	      return_type=>'array',
	      );
    $args{input_ids}=$input_ids if $input_ids;
    $args{input_ids_all}=$input_ids_all if $input_ids_all;

    my $table;
    eval { 
#	warn "$0: args are ",Dumper(\%args);
	$table=$babel->translate(%args);
#	warn "$0: table is ",Dumper($table);
    };
    confess $@ if $@;

    my $content=$io->format_table($table);
}



sub idtypes {
    my $table=[map {[$_->name,$_->display_name]} @{$babel->idtypes}];
    my $content=$io->format_table($table);
}

########################################################################

# These three are used by request_form()
sub hash_as_options {
    my ($hashref, $sorter)=@_;
    $sorter = sub { $a cmp $b } unless ref $sorter eq 'CODE';
    join("\n",map {"<option value='$hashref->{$_}'>$_</option>\n"} sort $sorter keys %$hashref);
}

sub array2d_as_options {
    my ($arrayref)=@_;
    join("\n",map "<option value='$_->[0]'>$_->[1]</option>", @$arrayref);
}

sub array2d_as_checkboxes {
    my (%argHash)=@_;
    my ($arrayref,$separator,$name,$checked)=@argHash{qw(arrayref separator name checked)};
    my $checked_str=defined $checked? "checked='1'" : '';
    join($separator,map "<input type='checkbox' name='$name' value='$_->[0]' $checked_str />$_->[1]", @$arrayref);
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
    "$error;\n";
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

main();
