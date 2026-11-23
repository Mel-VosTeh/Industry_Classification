// Neo4j Browser input; run :param separately from the query.
:param system => 'FIC_A';
:param code => 'A11';
// Parent -> child means ancestors are reached by following incoming edges.
MATCH (ancestor:ClassificationCode)-[:PARENT_OF*1..]->
      (c:ClassificationCode {system: $system, code: $code})
RETURN DISTINCT ancestor.system AS system, ancestor.code AS code, ancestor.name AS name
ORDER BY code;
