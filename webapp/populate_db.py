"""populating gene app tables

"""

import sqlite3 as sql
import sys
from collections import defaultdict
import cPickle

database = '/Users/jiggy/Documents/PhD Stuff/from backup/Cooccurrence vs Comembership/metanet/metanet.db'
con = sql.connect(database) 
cur = con.cursor()

con_path = sql.connect('/Users/jiggy/Documents/PhD Stuff/from backup/Cooccurrence vs Comembership/PathVantage/PathVantage.db')
cur_path = con_path.cursor()

def table_record_counts(tables=[]):
	if not tables:
		cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
		tables = [row[0] for row in cur.fetchall()]
	for table in tables:
		cur.execute("SELECT count(*) FROM %s"  % table)
		print table, cur.fetchall()[0][0]
	
def insert_gene():
	cur_path.execute("SELECT id,symbol FROM gene_gene WHERE species_id=9606")
	for row in cur_path:
		gene_id = row[0]
		gene_symbol = row[1]
		
		#print gene_id, gene_symbol
		#continue
		
		try:
			cur.execute('INSERT INTO "webapp_gene"	VALUES (?,?)', (gene_id, gene_symbol))
		except:
			print sys.exc_info()[1].message

def insert_kinphos():
	#add kinase and phosphatase substrates
	fh = open('/Users/jiggy/Documents/PhD Stuff/from backup/Cooccurrence vs Comembership/lists/pipeline/comembership/Kinase substrates__Phosphatase substrates.corrected.tab')
	fh.readline()
	genesets = {}
	for line in fh:
		line = line.strip().split("\t")
		genesets[line[0]] = line[2]
	fh.close()

	redundancy_map = {}
	cur_path.execute("SELECT id,name,subgroup,redundancies FROM geneset_geneset WHERE subgroup IN ('Kinase substrates', 'Phosphatase substrates')")
	for row in cur_path:
		geneset_id = row[0]
		geneset_name = row[1]
		geneset_subgroup = row[2]
		redundancies = row[3]
		
		if geneset_id not in genesets:
			for redundancy in redundancies.split(","):
				if redundancy in genesets:
					redundancy_map[redundancy] = geneset_id
		else:
			redundancy_map[geneset_id] = geneset_id
	
	#add genesets
	for geneset_id in genesets:
		geneset_name = genesets[geneset_id]
		if geneset_id[0] == 'K':
			geneset_subgroup = 'Kinase substrates'
		elif geneset_id[0] == 'P':
			geneset_subgroup = 'Phosphatase substrates'

		try:
			cur.execute('INSERT INTO "webapp_geneset"  VALUES (?,?,?)', (geneset_id, geneset_name, geneset_subgroup))
		except:
			print sys.exc_info()[1].message

		#add members
		cur_path.execute("SELECT gs.gene_id FROM geneset_geneset_members gs WHERE gs.geneset_id=?", (redundancy_map[geneset_id],))
	
		for row in cur_path:
			gene_id = row[0]
					
			try:
				cur.execute('INSERT INTO "webapp_geneset_members"  VALUES (NULL,?,?)', (geneset_id, gene_id))
			except:
				print sys.exc_info()[1].message
	
		
def insert_geneset():
	cur_path.execute("SELECT id,name,subgroup FROM geneset_geneset WHERE subgroup IN ('Chromosome map', 'KEGG PATHWAY', 'VirusMINT', 'WikiPathways', 'biological_process_50_10_200', 'cellular_component_50_10_200', 'molecular_function_50_10_200')")
	for row in cur_path:
		geneset_id = row[0]
		geneset_name = row[1]
		geneset_subgroup = row[2]
		
		if "_50_10_200" in geneset_id:
			geneset_id = geneset_id.replace("_50_10_200", "")		
				
		#print gene_id, gene_symbol
		#continue
		
		try:
			cur.execute('INSERT INTO "webapp_geneset"  VALUES (?,?,?)', (geneset_id, geneset_name, geneset_subgroup))
		except:
			print sys.exc_info()[1].message
				

def insert_geneset_members():
	cur_path.execute("SELECT gs.geneset_id, gs.gene_id FROM geneset_geneset_members gs, geneset_geneset g WHERE gs.geneset_id=g.id AND g.subgroup IN ('Chromosome map', 'KEGG PATHWAY', 'VirusMINT', 'WikiPathways', 'biological_process_50_10_200', 'cellular_component_50_10_200', 'molecular_function_50_10_200')")
	i = 0
	for row in cur_path:
		i += 1
		geneset_id = row[0]
		gene_id = row[1]
		if "_50_10_200" in geneset_id:
			geneset_id = geneset_id.replace("_50_10_200", "")
				
		#print gene_id, gene_symbol
		#continue
		
		try:
			cur.execute('INSERT INTO "webapp_geneset_members"  VALUES (?,?,?)', (i,geneset_id, gene_id))
		except:
			print sys.exc_info()[1].message

def insert_single_metanet(name, edges, metanet_id):
	try:
		cur.execute('INSERT INTO "webapp_metanetwork"  VALUES (?,?)', (metanet_id, name))
	except:
		print sys.exc_info()[1].message

	for edge in edges:
		term1, term2 = edge
		
		if "_50_10_200" in term1:
			term1 = term1.replace("_50_10_200", "")
			
		if "_50_10_200" in term2:
			term2 = term2.replace("_50_10_200", "")
			
		pval = edges[edge][0]
		benjamini = edges[edge][1]
		try:
			cur.execute('INSERT INTO "webapp_metanetworkedges"  VALUES (NULL,?,?,?,?,?)', (metanet_id, term1, term2, pval, benjamini))
		except:
			print sys.exc_info()[1].message
	
def insert_metanets():
	for name, comem_file in [('KEGG Pathway', 'KEGG'), ('Phosphorylation Substrates', 'Kinase substrates__Phosphatase substrates'), ('VirusMINT', 'VirusMINT'), ('WikiPathways', 'WikiPathways'), ('GO Biological Process Trim50', 'biological_process_50_10_200'), ('GO Cellular Component Trim50', 'cellular_component_50_10_200'), ('GO Molecular Function Trim50', 'molecular_function_50_10_200'), ('Chromosome Map', 'Chromosome map')]:
		#insert comembership
		name = name + ' Co-membership'
		metanet_id = comem_file + ' comembership'
		comem_file = '/Users/jiggy/Documents/PhD Stuff/from backup/Cooccurrence vs Comembership/lists/pipeline/comembership/' + comem_file + '.corrected.tab' 
		
		edges = {}
		fh = open(comem_file)
		fh.readline()
		for line in fh:
			line = line.strip().split('\t')
			if len(line) < 2:
				continue
			term1 = line[0]
			term2 = line[1]
			if not term1 or not term2:
				continue
			pval = float(line[-2])
			benjamini = float(line[-1])
			edges[(term1, term2)] = (pval, benjamini)

		insert_single_metanet(name, edges, metanet_id)
		fh.close()

	for name, coint_file in [('KEGG Pathway', 'KEGG'), ('Phosphorylation Substrates', 'Kinase substrates__Phosphatase substrates'), ('VirusMINT', 'VirusMINT'), ('WikiPathways', 'WikiPathways'), ('GO Biological Process Trim50', 'biological_process_50_10_200'), ('GO Cellular Component Trim50', 'cellular_component_50_10_200'), ('GO Molecular Function Trim50', 'molecular_function_50_10_200'), ('Chromosome Map', 'Chromosome map')]:
		#insert cointeraction
		name = name + ' Linkage: PPI'
		metanet_id = coint_file + ' linkage_ppi'
		coint_file = '/Users/jiggy/Documents/PhD Stuff/from backup/Cooccurrence vs Comembership/lists/pipeline/linkage_ppi/' + coint_file + '.corrected.tab' 

		edges = {}
		fh = open(coint_file)
		fh.readline()
		for line in fh:
			line = line.strip().split('\t')
			if len(line) < 2:
				continue
			term1 = line[0]
			term2 = line[1]
			if not term1 or not term2:
				continue
			pval = float(line[6])
			benjamini = float(line[7])
			edges[(term1, term2)] = (pval, benjamini)

		insert_single_metanet(name, edges, metanet_id)
		fh.close()	  


	for name, coexp_file in [('KEGG Pathway', 'KEGG'), ('Phosphorylation Substrates', 'Kinase substrates__Phosphatase substrates'), ('VirusMINT', 'VirusMINT'), ('WikiPathways', 'WikiPathways'), ('GO Biological Process Trim50', 'biological_process_50_10_200'), ('GO Cellular Component Trim50', 'cellular_component_50_10_200'), ('GO Molecular Function Trim50', 'molecular_function_50_10_200'), ('Chromosome Map', 'Chromosome map')]:
		#insert coexpression
		name = name + ' Co-enrichment: Differential Expression'
		metanet_id = coexp_file + ' coenrichment_differential_expression'
		coexp_file = '/Users/jiggy/Documents/PhD Stuff/from backup/Cooccurrence vs Comembership/lists/pipeline/coexpression/' + coexp_file + '.tab.benjamini.tab' 

		edges = {}
		fh = open(coexp_file)
		fh.readline()
		for line in fh:
			line = line.split('\t')
			if len(line) < 2:
				continue
			term1 = line[0]
			term2 = line[1]
			if not term1 or not term2:
				continue
			pval = float(line[2])
			benjamini = float(line[3])
			edges[(term1, term2)] = (pval, benjamini)

		insert_single_metanet(name, edges, metanet_id)
		fh.close()

if __name__ == "__main__":
	print
	print "inserting gene"	
	insert_gene()
	print
	print "inserting geneset"	
	insert_geneset()
	print
	print "inserting geneset_members"	
	insert_geneset_members()
	print
	print "inserting insert_kinphos"
	insert_kinphos()
	print
	print "inserting metanets"	
	insert_metanets()
	
	con.commit()
	
	print
	print "Table Counts"
	table_record_counts()
	  
	cur_path.close()
	con_path.close()

	cur.close()
	con.close()


#
#
