; Tree-sitter queries for Haskell
; These queries define how to extract symbols from the Haskell AST

; Module declarations
(module
  (module_id) @module.name) @module

; Import statements
(import
  (module_id) @import.module
  (import_alias)? @import.alias) @import

(import
  "qualified" @import.qualified
  (module_id) @import.module) @import

; Type signatures
(signature
  name: (variable_id) @function.name
  type: (_) @function.type) @function.signature

; Function bindings
(function_binding
  name: (variable_id) @function.name) @function

; Data type declarations
(data_declaration
  name: (type_constructor_id) @type.name) @type.data

; Newtype declarations
(newtype_declaration
  name: (type_constructor_id) @type.name) @type.newtype

; Type synonyms
(type_synonym_declaration
  name: (type_constructor_id) @type.name) @type.alias

; Type class declarations
(class_declaration
  name: (class_id) @class.name) @class

; Instance declarations
(instance_declaration
  class: (class_id) @instance.class) @instance

; Type family declarations
(type_family_declaration
  name: (type_constructor_id) @type.family) @type.family

; Data family declarations
(data_family_declaration
  name: (type_constructor_id) @type.family) @type.family

; Fixity declarations
(fixity_declaration
  (infix_id) @operator.name
  precedence: (integer_literal) @operator.precedence) @operator

; Pattern bindings
(pattern_binding
  pattern: (as_pattern
    variable: (variable_id) @binding.name)) @binding

; Let bindings
(let_expression
  bindings: (bindings
    (signature
      name: (variable_id) @local.name) @local.signature
    (function_binding
      name: (variable_id) @local.name) @local.function))

; Where bindings
(where_clause
  bindings: (bindings
    (signature
      name: (variable_id) @local.name) @local.signature
    (function_binding
      name: (variable_id) @local.name) @local.function))

; Record fields
(field_declaration
  names: (field_name) @field.name
  type: (_) @field.type) @field

; Constructor declarations
(data_constructor
  (constructor_id) @constructor.name) @constructor

; GADT constructors
(gadt_constructor
  names: (constructor_id) @constructor.name
  type: (_) @constructor.type) @constructor.gadt

; Language pragmas
(pragma
  (language_pragma
    (pragma_name) @pragma.language)) @pragma

; Other pragmas
(pragma
  (pragma_name) @pragma.name
  (pragma_content) @pragma.content) @pragma

; Comments and documentation
(comment) @comment
(haddock_comment) @documentation

; Top-level declarations
(declarations
  (signature) @declaration.signature
  (function_binding) @declaration.function
  (data_declaration) @declaration.data
  (newtype_declaration) @declaration.newtype
  (type_synonym_declaration) @declaration.type
  (class_declaration) @declaration.class
  (instance_declaration) @declaration.instance)

; Qualified names
(qualified_variable_id
  module: (module_id) @qualified.module
  variable: (variable_id) @qualified.name) @qualified

(qualified_constructor_id
  module: (module_id) @qualified.module
  constructor: (constructor_id) @qualified.name) @qualified

(qualified_type_constructor_id
  module: (module_id) @qualified.module
  type: (type_constructor_id) @qualified.name) @qualified

; Infix operators
(infix_operator_application
  operator: (infix_id) @operator.use) @expression.infix

; Type applications
(type_application
  function: (_) @type.function
  argument: (_) @type.argument) @type.application

; List comprehensions
(list_comprehension
  expression: (_) @comprehension.expression
  qualifiers: (_) @comprehension.qualifiers) @comprehension.list

; Do notation
(do_expression
  (statement) @do.statement) @expression.do

; Case expressions
(case_expression
  expression: (_) @case.expression
  alternatives: (alternatives) @case.alternatives) @expression.case

; Lambda expressions
(lambda_expression
  parameters: (_) @lambda.parameters
  body: (_) @lambda.body) @expression.lambda

; Guards
(guard
  condition: (_) @guard.condition
  expression: (_) @guard.expression) @guard

; Pattern matching
(pattern_guard
  pattern: (_) @pattern.match
  expression: (_) @pattern.expression) @pattern.guard

; Type constraints
(constraint
  class: (class_id) @constraint.class
  type: (_) @constraint.type) @constraint

; Deriving clauses
(deriving_clause
  (class_id) @deriving.class) @deriving

; Export lists
(export_list
  (export) @export.item) @export.list

; Import lists
(import_list
  (import_item) @import.item) @import.list