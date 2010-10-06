package BabelClient;
use strict;
use warnings;

use Carp;
use Data::Dumper;
use LWP::UserAgent;
use HTTP::Request::Common;
use JSON;

use HasAccessors qw(:all);
use base qw(HasAccessors);
add_accessors(qw());
add_accessors_with_defaults(base_url=>'http://babel.gdxbase.org/cgi-bin/translate.cgi',
    );
add_class_accessors_with_defaults(ua=>LWP::UserAgent->new);

require_attrs(qw());

sub new {
    my ($proto,%args)=@_;
    my $class = ref $proto || $proto;
    my $self=$class->SUPER::new(%args);

    # object initialization goes here as needed

    $self;
}


sub idtypes {
    my ($self,%argHash)=@_;
    my %args=(request_type=>'idtypes',
	output_format=>'json');
    @args{keys %argHash}=@{values %argHash} if %argHash;
#    warn "idtypes: args are ",Dumper(\%args);
	      
    my $content=$self->_fetch(%args);
    my $table=decode_json($content);
    wantarray? @$table:$table;
}

sub translate {
    my ($self,%argHash)=@_;
    my %args=(request_type=>'translate', output_format=>'json');
    delete @argHash{keys %args}; # override values
    @args{keys %argHash}=values %argHash if %argHash;

    my @missing_args;
    my @required_args=qw(request_type input_ids input_type output_types output_format);
    push @missing_args, grep /\w/, map {$args{$_}? '' : $_} @required_args;
    die sprintf("translate: missing args: %s\n", join(', ',@missing_args)) if @missing_args;
    
    my $json=$self->_fetch(%args);
    my $table=decode_json($json);
    wantarray? @$table:$table;
}

sub _fetch {
    my ($self,%args)=@_;
    my $req=POST($self->base_url,\%args);
    my $res=$self->ua->request($req);

    die sprintf("babel webservice error: %s\n",$res->status_line)
	unless $res->is_success;
    $res->content;
}


1;
