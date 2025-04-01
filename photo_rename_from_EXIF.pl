#!/usr/bin/env perl
# alt: !/usr/bin/perl

# by Torben Menke https://entorb.net

# DESCRIPTION
# works on all .jpe?g files in and below current dir
# extracts the exif tags from the image
# checks for tag 'Image Generated'
# renames the image file to prepend the date in format 180929_114641_

# TODO

# IDEAS

# DONE

# Modules: My Default Set
use strict;
use warnings;
use 5.010;    # say
use Data::Dumper;
use autodie qw (open close);    # Replace functions with ones that succeed or die: e.g. close
use utf8;                       # this script is written in UTF-8
# binmode default encoding for print STDOUT
if ( $^O eq 'MSWin32' ) {
  binmode( STDOUT, ':encoding(cp850)' );
} else {
  binmode( STDOUT, ':encoding(UTF-8)' );
}

# pp -M Image::EXIF -o Photo-Rename_From_EXIF.exe Photo-Rename_From_EXIF.pl

# Modules: Perl Standard
# use Encode qw(encode decode);
# use open ":encoding(UFT-8)";    # for all files
# my $encodingSTDOUT = 'CP850';   # Windows/DOS: 'CP850'; Linux: UTF-8

# Modules: File Access
use File::Basename;    # for basename, dirname, fileparse
use File::Path qw(make_path remove_tree);

# Modules: CPAN
# use LWP::UserAgent; # http requests
# use Excel::Writer::XLSX;
# perl -MCPAN -e "install Excel::Writer::XLSX"
use Image::EXIF;

# traverse
my $path = shift || '.';
traverse( $path );


sub traverse {
  my @queue = @_;
  while ( @queue ) {
    my $thing = shift @queue;
    if ( -f $thing and $thing =~ m/\.jpe?g$/i ) {
      # say $thing;
      exifrename( $thing );
    }
    next if not -d $thing;
    opendir my $dh, $thing or die;
    while ( my $sub = readdir $dh ) {
      next if $sub eq '.' or $sub eq '..';
      push @queue, "$thing/$sub";
    }
    closedir $dh;
  }
  return;
}


sub exifrename {
  my ( $file ) = @_;

  # my $file  = '1 2 34/TME_0915.jpg';
  # my $fdir  = dirname( $file );
  # my $fname = basename( $file );
  my ( $fname, $fdir, $fext ) = fileparse( $file, qr/\.[^.]*/ );
  $fext = "\L$fext";    # lower ext.
  $fext =~ s/jpeg/jpg/;
  say $fname;

  return 0 if $fname =~ m/^\./;    # no . files

  if ( $fname =~ m/^\d{6}_\d{6}_/ ) {
    say " W: seams like to start with correct dateformat already, skipping";
    return 0;
  }

  die " E: can't find/open file '$file'" unless -f $file;
  my $exif = Image::EXIF->new( $file ) or return 0;

  my $exif_info = $exif->get_other_info();    # get_all_info() , get_image_info(), get_other_info()
  if ( not defined $exif_info ) {
    say " W: no exif tag found, skipping";
    return 0;
  }
  %_ = %{ $exif_info };
  # say Dumper $exif->get_all_info();
  my $imageDate = $_{ 'Image Generated' };    # 2018:09:29 11:46:41

  if ( not defined $imageDate or $imageDate eq '' or not length( $imageDate ) == 19 or $imageDate eq '0000:00:00 00:00:00' ) {    # 2018:09:29 11:46:41
    print Dumper $exif->get_all_info();
    say " W: field 'Image Generated': '$imageDate' not valid in file $file, skipping";
    return 0;
  }

  # 2018:09:29 11:46:41 -> 180929_114641
  my $datestr = substr( $imageDate, 2, length( $imageDate ) - 2 );
  $datestr =~ s/://g;
  $datestr =~ s/ /_/g;
  # say $datestr;

  my $fileNew = $fdir . '/' . $datestr . '_' . $fname.$fext;

  if ( -f $fileNew ) {
    say " W: file '$fileNew' already present, so skipping file '$file'";
    return 0;
  }

  say "$file -> $fileNew";
  rename $file, $fileNew unless -f $fileNew;
}
