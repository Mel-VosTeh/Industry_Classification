:param system => 'FIC_A';
:param code => 'A21';
// Either endpoint counts as directly mapped. Preserve stored direction in output.
MATCH (c:ClassificationCode {system: $system, code: $code})-[m:MAPS_TO]-(other)
WHERE c.system <> other.system
RETURN startNode(m).system AS source_system, startNode(m).code AS source_code,
       endNode(m).system AS target_system, endNode(m).code AS target_code,
       m.mapping_type AS mapping_type, m.provenance AS provenance,
       m.confidence AS confidence
ORDER BY target_code;
