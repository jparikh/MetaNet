"""Models for the webapp
"""

from django.db import models

# Create your models here.

class Gene(models.Model):
	#Entrez Gene
	id = models.IntegerField(primary_key=True, help_text="Entrez Gene ID")
	symbol = models.CharField(db_index=True, max_length=30, blank=True, help_text="Official Gene Symbol")
	
	def __unicode__(self):
		return self.symbol	  

class GeneSet(models.Model):
	id = models.CharField(primary_key=True, max_length=100, help_text="Gene Set ID")
	name = models.CharField(max_length=200, help_text="Gene Set Name")
	subgroup = models.CharField(max_length=50, help_text="Gene Set Group. Specific grouping like 'KEGG PATHWAY'")	# cannot be blank
	members = models.ManyToManyField(Gene, help_text="GeneSet Members")	 # cannot be blank

	def __unicode__(self):
		return self.name	

class MetaNetwork(models.Model):
	id = models.CharField(primary_key=True, max_length=100, help_text="Meta-Network ID")
	name = models.CharField(max_length=200, help_text="Meta-Network Name")

	def __unicode__(self):
		return self.name	

class MetaNetworkEdges(models.Model):
    network = models.ForeignKey(MetaNetwork, help_text="Meta-Network")
    term1 = models.ForeignKey(GeneSet, related_name="term1_geneset", help_text="Term1")
    term2 = models.ForeignKey(GeneSet, related_name="term2_geneset", help_text="Term2")
    pvalue = models.FloatField(help_text="Uncorrected P-Value")
    benjamini = models.FloatField(help_text="Benjamini P-Value")

    def __unicode__(self):
        return self.term1.name + '--' + self.term2.name
	