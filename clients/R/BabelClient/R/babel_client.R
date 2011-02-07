require("RCurl")
require("rjson")
#---------------------------------------------------------------------------------
.onLoad <- function (libname, pkgname)
{
  print("babel_client.R loaded")

} # .onLoad
#---------------------------------------------------------------------------------
idtypes <- function() {
  url <- "http://babel.gdxbase.org/cgi-bin/translate.cgi"
  res <- postForm(url, "request_type"="idtypes", "output_format"="r")  
  print(res)
  data <- fromJSON(res, method="R")
  return(data)
}

translate <- function(input_type,input_ids,output_types) {
  url <- "http://babel.gdxbase.org/cgi-bin/translate.cgi"
  res <- postForm(url, "request_type"="translate", 
                       "input_type"=input_type,
                       "input_ids"=input_ids,
                       "output_types"=output_types,
                       "output_format"="r")  
  data <- fromJSON(res, method="R")
  return(data)
}

#translate_test <- function() {
#  return(translate(input_type='gene_entrez',input_ids='8923,9283,21378,21389',output_types='gene_symbol,gene_ensembl,function_go'))
#}
#translate_test2 <- function() {
#  return(translate(input_type='gene_entrez',input_ids='8923,9283,21378,21389',output_types=c('gene_symbol','gene_ensembl','function_go')))
#}


