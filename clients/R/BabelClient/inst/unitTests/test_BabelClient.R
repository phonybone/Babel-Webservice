library (BabelClient)
library (RUnit)
#------------------------------------------------------------------------------------------------------------------------
test.idtypes = function ()
{
  result = idtypes ()
  result.expanded = unlist (result)
  checkTrue (length (result.expanded) > 50)
  checkTrue ('organism' %in% result.expanded)
  return (TRUE)

} # test.idtypes
#------------------------------------------------------------------------------------------------------------------------
test.translate = function ()
{
  result = translate (input_type='gene_entrez',input_ids='9283',output_types='gene_symbol')
  checkEquals (unlist (result), c ("9283", "GPR37L1"))
  return (TRUE)

} # test.translate
#------------------------------------------------------------------------------------------------------------------------
