; CSV Tree-sitter tags for symbol extraction

; Extract headers as symbols
(header
  (field) @name) @definition.field

; Extract row identifiers (first field as potential key)
(row
  (field) @name 
  (#is? @name 0)) @reference.record

; Statistical markers for numeric columns
(header
  (field) @name
  (#match? @name ".*_(count|total|sum|avg|amount|price|quantity)$")) @definition.metric

; Date columns
(header  
  (field) @name
  (#match? @name ".*(date|time|timestamp|created|updated|modified).*")) @definition.time

; ID columns
(header
  (field) @name
  (#match? @name ".*(id|ID|key|code|uuid)$")) @definition.identifier

; Status/State columns
(header
  (field) @name
  (#match? @name ".*(status|state|active|enabled).*")) @definition.enum