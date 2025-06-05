;; Tree-sitter query file for YAML symbol extraction
;; This file defines patterns for extracting symbols from YAML files

;; Top-level keys (main configuration sections)
(document
  (block_mapping
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.key.toplevel))))

;; Nested keys with path context
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.key)
  value: (flow_node))

;; Service names in Docker Compose
(document
  (block_mapping
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.services
        (#eq? @symbol.services "services"))
      value: (flow_node
        (block_mapping
          (block_mapping_pair
            key: (flow_node (plain_scalar) @symbol.service.name)))))))

;; Kubernetes resource definitions
(document
  (block_mapping
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.k8s.kind.key
        (#eq? @symbol.k8s.kind.key "kind"))
      value: (flow_node (plain_scalar) @symbol.k8s.kind.value))
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.k8s.apiversion.key
        (#eq? @symbol.k8s.apiversion.key "apiVersion"))
      value: (flow_node (plain_scalar) @symbol.k8s.apiversion.value))
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.k8s.metadata.key
        (#eq? @symbol.k8s.metadata.key "metadata"))
      value: (flow_node
        (block_mapping
          (block_mapping_pair
            key: (flow_node (plain_scalar) @symbol.k8s.name.key
              (#eq? @symbol.k8s.name.key "name"))
            value: (flow_node (plain_scalar) @symbol.k8s.name.value)))))))

;; GitHub Actions jobs
(document
  (block_mapping
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.gh.jobs.key
        (#eq? @symbol.gh.jobs.key "jobs"))
      value: (flow_node
        (block_mapping
          (block_mapping_pair
            key: (flow_node (plain_scalar) @symbol.gh.job.name)))))))

;; GitHub Actions workflow triggers
(document
  (block_mapping
    (block_mapping_pair
      key: (flow_node (plain_scalar) @symbol.gh.on.key
        (#eq? @symbol.gh.on.key "on"))
      value: (flow_node) @symbol.gh.on.value)))

;; Anchors (reusable configuration blocks)
(anchor) @symbol.anchor

;; Aliases (references to anchors)
(alias) @symbol.alias

;; Array items with significant values
(block_sequence
  (block_sequence_item
    (flow_node (plain_scalar) @symbol.array.item)))

;; Environment variables
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.env.key
    (#match? @symbol.env.key "^[A-Z_]+[A-Z0-9_]*$"))
  value: (flow_node) @symbol.env.value)

;; Port mappings
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.port.key
    (#eq? @symbol.port.key "ports"))
  value: (flow_node
    (block_sequence
      (block_sequence_item
        (flow_node (plain_scalar) @symbol.port.mapping)))))

;; Volume mappings
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.volume.key
    (#eq? @symbol.volume.key "volumes"))
  value: (flow_node) @symbol.volume.value)

;; Network definitions
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.network.key
    (#eq? @symbol.network.key "networks"))
  value: (flow_node) @symbol.network.value)

;; Docker image references
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.image.key
    (#eq? @symbol.image.key "image"))
  value: (flow_node (plain_scalar) @symbol.image.value))

;; Container names
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.container.key
    (#eq? @symbol.container.key "container_name"))
  value: (flow_node (plain_scalar) @symbol.container.value))

;; Configuration file includes
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.include.key
    (#match? @symbol.include.key "(include|extends|import)"))
  value: (flow_node (plain_scalar) @symbol.include.value))

;; Tags and labels
(block_mapping_pair
  key: (flow_node (plain_scalar) @symbol.label.key
    (#match? @symbol.label.key "(tags?|labels?)"))
  value: (flow_node) @symbol.label.value)