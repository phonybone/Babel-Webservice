package Data::Babel::IO;
use strict;
use warnings;

use base qw(Class::AutoClass);
use Carp;
use Data::Dumper;
use CGI;
use Options;
use XML::Simple;
use Text::CSV;
use JSON;

use vars qw(@AUTO_ATTRIBUTES @CLASS_ATTRIBUTES %DEFAULTS %SYNONYMS);
@AUTO_ATTRIBUTES = qw(request trans_params cgi_params idtypes formats is_webpage);
@CLASS_ATTRIBUTES = qw();
%DEFAULTS = (trans_params=>[qw(input_type output_types output_format)],
	     cgi_params=>[qw(input_type input_ids output_types output_format request_type input_ids_all)],
	     formats=>{HTML=>'html', XML=>'xml', JSON=>'json', 'Comma separated'=>'csv', 'Tab separated'=>'tsv', R=>'r'},
	     );
%SYNONYMS = ();

Class::AutoClass::declare(__PACKAGE__);

sub _init_self {
    my ($self, $class, $args) = @_;
    return unless $class eq __PACKAGE__; # to prevent subclasses from re-running this

    confess "no idtypes (ARRAY ref)" unless ref $self->idtypes eq 'ARRAY';

    $self->is_webpage(1) unless defined $self->is_webpage;

    $self->get_request();
    $self->verify_request();
}


sub get_request {
    my ($self)=@_;
    my ($cgi,%request);

    # create a cgi object, depending on how script was called:
    if (!$self->is_webpage) {
	my @options=map {"$_:s"} (@{$self->cgi_params}, 'config_file');
	Options::use(@options);
	Options::useDefaults(input_ids=>[],output_types=>[]);
	Options::get();
	
	if ($options{config_file}) {
	    open (CONFIG, $options{config_file}) or die "Can't read $options{config_file}: $!";
	    $cgi=new CGI(\*CONFIG);
	    close CONFIG;

	} else {
	    $cgi=new CGI(\%options);
	}
    } else {
	$cgi=new CGI;
    }

    # copy $cgi into %request; probably could do this with $cgi->Vars
    foreach my $p (@{$self->cgi_params}) {
	$request{$p}=$cgi->param($p);
    }

    # deal with params that should be lists:
    foreach my $p (qw(input_ids output_types)) {
	if (my @val=$cgi->param($p)) {
	    $request{$p}=[map {split(/[\s,]+/,$_)} @val]; # flatten list
	}
    }

    # should taint-check all input...

    $self->request(\%request);
#    warn "get_request: request: ",Dumper(\%request);
}

sub verify_request {
    my ($self)=@_;
    my $request=$self->request or confess "request not set; call get_request first";

    my (@errors,@missing);

    my $request_type = $request->{request_type} ||= 'request_form';

    if ($request->{request_type} eq 'request_form') {
	$request->{output_format}='html';

    } elsif ($request->{request_type} eq 'idtypes') {
	my $output_format=$request->{output_format};
	if (!defined $output_format) {
	    push @errors, "Missing params: output_format";
	}

    } elsif ($request_type eq 'translate') {
	# missing input:
	foreach my $p (@{$self->trans_params}) {
	    if (!defined $request->{$p} ||
		(ref $request->{$p} eq 'ARRAY' && @{$request->{$p}}==0)) {
		push @missing, $p;
	    }
	}

	# special case for input_ids and input_all_ids: must have one or the 
	# other, not both:
	my ($input_ids,$input_ids_all)=@$request{qw(input_ids input_ids_all)};
	if ($input_ids) {
	    if (ref $input_ids && @$input_ids > 0) {
		if ($input_ids_all) {
		    push @errors, "Both input_ids and input_all_ids present";
#		    warn sprintf "%d input_ids, input_ids_all=$input_ids_all", scalar @$input_ids;
		}
	    } else {
		push @errors, "Invalid value for input_ids; not a list ref ($input_ids)";
	    }
	} elsif (!$input_ids_all) {
	    push @missing, "input_ids or input_all_ids";
	}

	if (@missing) {
	    my $err=sprintf "Missing params: %s",join(', ',@missing);
	    push @errors,$err;
	}

	# unknown types
	my @idtypes=map {$_->name} @{$self->idtypes};
	foreach my $t ($request->{input_type},@{$request->{output_types}}) {
	    next unless defined $t;	# could be repeat of above?
	    push @errors, "'$t': unknown type" unless grep /^$t$/, @idtypes;
	}

    } else {
	push @errors, "Unknown request type '$request_type'" unless $request_type eq 'request_form';
    }

    if (my $output_format=$request->{output_format}) {
	push @errors, "Unknown output format: '$output_format'" unless grep /^$output_format$/, values %{$self->formats};
    }


#    check_taint(\%request,\@errors);

    if (@errors) {
#	warn "errors are ",Dumper(\@errors);
	my $s=(@errors==1? '':'s');
	my $err=sprintf "Error$s: %s", join("\n",@errors);
	die "$err\n";
    }
}

sub check_taint {
    my ($self,$request,$errors)=@_;

    foreach my $param (@{$self->cgi_params}) {
	my $value=$request->{$param} or next;
	
	$value=~s/[^\w_-]//g;
        $request->{$param}=$value;	
    }
}


sub get_mimetype {
    my ($self)=@_;
    my $format=$self->request->{output_format} || 'unknown';

    # set content (mime) type:
    my $mimetype={html=>'text/html',
		  xml=>'text/plain',
		  json=>'application/json',
		  csv=>'text/plain',
		  tsv=>'text/plain',
		  R=>'text/plain',
		  unknown=>'text/plain'}->{$format}; 
}

########################################################################

sub format_table {
    my ($self,$table)=@_;
    my $format=$self->request->{output_format};
    my $formatter="as_$format";
    no strict "refs";
    my $content=$self->$formatter($table);
    use strict "refs";
    $content;
}

sub as_html {
    my ($self,$translations)=@_;
    my $output_display_names=$self->output_display_names();
    my $html=array2d_as_html_table(data=>$translations, col_names=>$output_display_names);
}

sub as_csv {
    my ($self,$translations)=@_;
    $self->as_ctsv($translations,",");
}

sub as_tsv {
    my ($self,$translations)=@_;
    $self->as_ctsv($translations,"\t");
}

sub as_ctsv {
    my ($self,$translations,$sep_char)=@_;
    my $tsv=Text::CSV->new({sep_char=>$sep_char, eol=>"\n",});

    my @header=$self->output_display_names();
    $tsv->combine(@header);
    my $content="# ".$tsv->string;

    foreach my $row (@$translations) {
	$tsv->combine(@$row) or die "error creating tsv table: ",$tsv->status;
	$content.=$tsv->string;
    }
    $content;
}

sub as_json {
    my ($self,$translations)=@_;
    my $json=encode_json($translations);
}


sub as_r {
    my ($self,$translations)=@_;
    my $json=encode_json($translations);
}


sub as_r1 {
    my ($self,$translations)=@_;
    my $header=join("\n",$self->output_display_names());
    array2d_as_table(data=>$translations, header=>"$header\n", row_sep=>"\t");
}

sub as_xml {
    my ($self,$translations)=@_;
    my $request=$self->request;
    my $input_type=$request->{input_type};
    my $output_types=$request->{output_types};
    my @input_ids=$request->{input_ids};

    my $hashlist;
    foreach my $t (@$translations) {
	my $input_id=shift @$t;
	if (scalar @$t != scalar @$output_types) { # fixme: catch this exception
	    die(sprintf "bad row size %d vs %d", scalar @$t, (scalar @$output_types)+1);
	}
	my %hash;
	@hash{@$output_types}=@$t; # fixme: how to make output types visible? as attr?
	push @$hashlist,{output_ids=>\%hash, input_id=>$input_id};
    }
    
    my $p=new XML::Simple(ForceArray=>[qw(translation)], KeyAttr=>{}, NoAttr=>1, RootName=>'Babel');
    $p->XMLout({translations=>{translation=>$hashlist}});
}

# return an array(ref) of display names for the output types
# display names
sub output_display_names {
    my ($self)=@_;
    my $request=$self->request;

    my $request_type=$request->{request_type};
    my @display_names;
    if ($request_type eq 'translate') {
	my %name2displayname=map {($_->name,$_->display_name)} @{$self->idtypes};
	@display_names=map {$name2displayname{$_}} @{$request->{output_types}};
	unshift @display_names,$name2displayname{$request->{input_type}}; 
    } elsif ($request_type eq 'idtypes') {
	@display_names=qw(name display_name);
    } else {
	die "unknown request_type '$request_type'";
    }
    wantarray? @display_names:\@display_names;
}

sub array2d_as_table {
    my %argHash=@_;
    my %defaults=(header=>'', footer=>'', row_header=>'', row_footer=>"\n", row_sep=>' ');
    while (my ($k,$v)=each %defaults) { $argHash{$k}=$v unless defined $argHash{$k} }
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

1;
