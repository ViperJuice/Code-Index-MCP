;; Tree-sitter query file for YAML syntax highlighting
;; This file defines patterns for identifying different YAML constructs

;; Keys (property names)
(block_mapping_pair
  key: (flow_node) @key)

(flow_mapping_pair
  key: (flow_node) @key)

;; String values
(double_quote_scalar) @string
(single_quote_scalar) @string
(plain_scalar) @string

;; Numbers
(plain_scalar) @number
  (#match? @number "^[0-9]+$")

(plain_scalar) @float
  (#match? @float "^[0-9]*\\.[0-9]+$")

;; Booleans
(plain_scalar) @boolean
  (#match? @boolean "^(true|false|yes|no|on|off)$")

;; Null values
(plain_scalar) @null
  (#match? @null "^(null|~|)$")

;; Anchors and aliases
(anchor) @anchor
(alias) @alias

;; Comments
(comment) @comment

;; Document separators
"---" @document.separator
"..." @document.separator

;; Tags
(tag) @tag

;; Directives
(directive) @directive

;; Block sequences (arrays)
(block_sequence) @array
(flow_sequence) @array

;; Block mappings (objects)
(block_mapping) @object
(flow_mapping) @object

;; Special YAML constructs
(block_literal) @string.special
(block_folded) @string.special