// Check incoming AND outgoing cross-system mappings, including isolated roots.
MATCH (c:ClassificationCode)
WHERE NOT EXISTS {
  MATCH (c)-[:MAPS_TO]-(other:ClassificationCode)
  WHERE other.system <> c.system
}
RETURN c.system AS system, c.code AS code, c.name AS name
ORDER BY system, code;
