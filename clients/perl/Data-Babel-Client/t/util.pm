package t::util;
# use t::lib;
use Carp;
use FindBin;
use File::Basename qw(fileparse);
use Cwd qw(cwd);
use Test::More;
use Test::Deep;
# Test::Deep doesn't export cmp_details, deep_diag until recent version (0.104)
# so we import them "by hand"
*cmp_details=\&Test::Deep::cmp_details;
*deep_diag=\&Test::Deep::deep_diag;
use Exporter();
use strict;

our @ISA=qw(Exporter);
our @EXPORT=qw(script scriptpath scriptfullpath scriptcode rootpath
	       as_bool flatten
	       cmp_quietly report report_pass report_fail
	     );
our($SCRIPT,$SCRIPTPATH,$SCRIPTCODE,$ROOTPATH);
sub script {$SCRIPT or (($SCRIPT,$SCRIPTPATH)=fileparse($0) and $SCRIPT);}
sub scriptpath {$SCRIPTPATH or (($SCRIPT,$SCRIPTPATH)=fileparse($0) and $SCRIPTPATH);}
sub scriptfullpath {$FindBin::Bin}
sub scriptcode {$SCRIPTCODE or (($SCRIPTCODE)=script=~/\.(\w+)\.t$/)[0];}
sub rootpath {$ROOTPATH or $ROOTPATH=cwd}

sub as_bool {$_[0]? 1: 0}
sub flatten {map {'ARRAY' eq ref $_? @$_: $_} @_}

# like cmp_deeply but reports errors the way we want
sub cmp_quietly {
  my($actual,$correct,$label,$file,$line)=@_;
  return 1 if !defined($actual) && !(defined $correct);
  report_fail(defined $actual,"$label: defined",$file,$line) or return 0;
  my($ok,$details)=cmp_details($actual,$correct);
  report_fail($ok,"$label",$file,$line,$details);
}

sub report {
  my($ok,$label,$file,$line,$details)=@_;
  pass($label), return 1 if $ok;
  ($file,$line)=called_from($file,$line);
  fail($label);
  diag("from $file line $line") if defined $file;
  if (defined $details) {
    diag(deep_diag($details)) if ref $details;
    diag($details) unless ref $details;
  }
  return 0;
}
sub report_pass {
  my($ok,$label)=@_;
  pass($label) if $ok;
  $ok;
}
sub report_fail {
  my($ok,$label,$file,$line,$details)=@_;
  return 1 if $ok;
  ($file,$line)=called_from($file,$line);
  fail($label);
  diag("from $file line $line") if defined $file;
  if (defined $details) {
    diag(deep_diag($details)) if ref $details;
    diag($details) unless ref $details;
  }
  return 0;
}

# set $file,$line if not already set
sub called_from {
  return @_ if $_[0];
  my($package,$file,$line);
  my $i=0;
  while (($package,$file,$line)=caller($i++)) {
    last if 'main' eq $package;
  }
  ($file,$line);
}

################################################################################
# code below here is mostly from other modules
# trash if we don't end up using it...
################################################################################

# # TODO: rewrite w/ Hash::AutoHash::MultiValued
# # group a list by categories returned by sub.
# # has to be declared before use, because of prototype
# sub group (&@) {
#   my($sub,@list)=@_;
#   my %groups;
#   for (@list) {
#     my $group=&$sub($_);
#     my $members=$groups{$group} || ($groups{$group}=[]);
#     push(@$members,$_);
#   }
#   wantarray? %groups: \%groups;
# }
# # like group, but processes elements that are put on list. 
# # sub should return 2 element list: 1st defines group, 2nd maps the value
# # has to be declared before use, because of prototype
# sub groupmap (&@) {
#   my($sub,@list)=@_;
#   my %groups;
#   for (@list) {
#     my($group,$value)=&$sub($_);
#     my $members=$groups{$group} || ($groups{$group}=[]);
#     push(@$members,$value);
#   }
#   wantarray? %groups: \%groups;
# }

# # specialized group: sub should return true or false
# # true elements added to group 'ok'; false elements added to 'fail'
# # has to be declared before use, because of prototype
# sub groupcmp (&@) {
#   my($sub,@list)=@_;
#   my %cmp;			# keys will be 'pass', 'fail'
#   for (@list) {
#     my $group=&$sub($_)? 'pass': 'fail';
#     my $members=$groups{$group} || ($groups{$group}=[]);
#     push(@$members,$_);
#   }
#   wantarray? %groups: \%groups;
# }

# # $actual,$correct are HASHES. 
# # like cmp_deeply but reports errors the way we want
# sub cmp_hashes {
#   my($actual,$correct,$label,$file,$line)=@_;
#   return 1 if !defined($actual) && !(defined $correct);
#   report_fail(defined $actual,"$label: defined",$file,$line) or return 0;
#   my($ok,$details)=cmp_details($actual,$correct);
#   report_fail($ok,"$label",$file,$line,$details);
# }
# # $actual,$correct are ARRAYs. 
# # like cmp_deeply but reports errors the way we want
# sub cmp_lists {
#   my($actual,$correct,$label,$file,$line)=@_;
#   return 1 if !defined($actual) && !(defined $correct);
#   report_fail(defined $actual,"$label: defined",$file,$line) or return 0;
#   my($ok,$details)=cmp_details($actual,$correct);
#   report_fail($ok,"$label",$file,$line,$details);
# }
# # $actual is ARRAY of objects
# # $correct is ARRAY of HASHES, interpreted as methods and results
# sub cmp_objlists {
#   my($actual,$correct,$correct_class,$label,$file,$line)=@_;
#   return 1 if !defined($actual) && !(defined $correct);
#   report_fail(defined $actual,"$label: defined",$file,$line) or return 0;
#   my $actual_num=@$actual;
#   my $correct_num=@$correct;
#   report_fail(@$actual==$correct_num,
# 	      "$label: number of elements (is $actual_num should be $correct_num)",
# 	      $file,$line) or return 0;
#   for my $i (0..$correct_num-1) {
#     my $object=$actual->[$i];
#     report_fail(UNIVERSAL::isa($object,$correct_class),
# 		"$label: object $i class (is ".ref $object." should be $correct_class)",
# 		$file,$line) or return 0;
#     my $hash=$correct->[$i];
#     my($ok,$details)=cmp_details($object,methods(%$hash));
#     report_fail($ok,"$label: object $i contents",$file,$line,$details) or return 0;
#   }

# }


# TODO: if I keep them, these need to be moved earlier because of prototypes
# my $max_reports=5;
# sub report_cmp (\%;) {
#   my($cmp,$label,$reporter,$file,$line)=@_;
#   my $ok=!@{$cmp->{fail}||[]};
#   pass($label), return 1 if $ok;
#   _report_fail_cmp($cmp,$label,$reporter,$file,$line);
# }


# sub report_pass_cmp (\%;) {
#   my($cmp,$label)=@_;
#   my $ok=!@{$cmp->{fail}||[]};
#   pass($label) if $ok;
#   $ok;
# }
# sub report_fail_cmp (\%;) {
#   my($cmp,$label,$reporter,$file,$line)=@_;
#   my $ok=!@{$cmp->{fail}||[]};
#   return 1 if $ok;
#   _report_fail_cmp($cmp,$label,$reporter,$file,$line);
# }

# # when called, already know that test failed
# sub _report_fail_cmp {
#   my($cmp,$label,$reporter,$file,$line)=@_;
#   fail($label);
#   diag("from $file line $line") if defined $file;
#   my @pass=@{$cmp->{pass}||[]};
#   my @fail=@{$cmp->{fail}};
#   my @pass_reports=
#     map {UNIVERSAL::can($_,$reporter)? $_->$reporter: "$_"} @pass[0..min($max_reports-1,$#pass)];
#   my @fail_reports=
#     map {UNIVERSAL::can($_,$reporter)? $_->$reporter: "$_"} @fail[0..min($max_reports-1,$#fail)];
#   diag(scalar @pass.' elements passed. here are some: ',join('; ',@pass_reports));
#   diag(scalar @fail.' elements failed. here are some: ',join('; ',@fail_reports));
#   return 0;
# }

1;
