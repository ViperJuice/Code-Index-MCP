; CSV Tree-sitter highlighting queries

; Headers (first row)
(header
  (field) @variable.parameter)

; Field values
(row
  (field) @string)

; Delimiters
(delimiter) @punctuation.delimiter

; Quotes
(quote) @string.escape

; Numbers in fields
(field
  (#match? @number "^-?[0-9]+\\.?[0-9]*$")) @number

; Dates in fields  
(field
  (#match? @constant.builtin "^[0-9]{4}-[0-9]{2}-[0-9]{2}")) @constant.builtin

; Booleans
(field
  (#match? @constant.builtin.boolean "^(true|false|yes|no|TRUE|FALSE|YES|NO)$")) @constant.builtin.boolean

; Empty fields
(field
  (#eq? @comment "")) @comment

; Field with special characters
(escaped_field) @string.special