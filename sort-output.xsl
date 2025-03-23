<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="no"/>
	<xsl:template match="@*|node()">
		<xsl:copy>
			<xsl:apply-templates select="@*|node()" />
		</xsl:copy>
	</xsl:template>

	<xsl:template match="/checks">
		<checks>
			<!-- checks: repo -->
			<xsl:for-each select="/checks/result[not(category)]">
				<xsl:copy>
					<xsl:apply-templates>
						<xsl:sort select="class"/>
						<xsl:sort select="msg"/>
					</xsl:apply-templates>
				</xsl:copy>
			</xsl:for-each>

			<!-- checks: category -->
			<xsl:for-each select="/checks/result[category and not(package)]">
				<xsl:copy>
					<xsl:apply-templates>
						<xsl:sort select="category"/>
						<xsl:sort select="class"/>
						<xsl:sort select="msg"/>
					</xsl:apply-templates>
				</xsl:copy>
			</xsl:for-each>

			<!-- checks: cat/pn -->
			<xsl:for-each select="/checks/result[category and package and not(version)]">
				<xsl:copy>
					<xsl:apply-templates>
						<xsl:sort select="category"/>
						<xsl:sort select="package"/>
						<xsl:sort select="class"/>
						<xsl:sort select="msg"/>
					</xsl:apply-templates>
				</xsl:copy>
			</xsl:for-each>

			<!-- CPV -->
			<xsl:for-each select="/checks/result[category and package and version]">
				<xsl:copy>
					<xsl:apply-templates>
						<!-- multiple versions will likely share the same error message -->
						<xsl:sort select="category"/>
						<xsl:sort select="package"/>
						<xsl:sort select="class"/>
						<xsl:sort select="version"/>
						<xsl:sort select="msg"/>
					</xsl:apply-templates>
				</xsl:copy>
			</xsl:for-each>

		</checks>
	</xsl:template>

</xsl:stylesheet>
<!-- 
	vim: ts=2 sts=2 sw=2 
-->
