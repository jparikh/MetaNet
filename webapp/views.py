# Create your views here.
from django.template import Context, loader
from django.http import HttpResponse
from base64 import decodestring
from reportlab.pdfgen import canvas

from django.utils import simplejson
import enrichment
from webapp.models import *
from collections import defaultdict
from math import log10
from lxml import etree
import networkx as nx
import copy


annotations = defaultdict(set)
names = {}
enrichment_results = []
gene_map = defaultdict(set)

def png(request):
	data = request.raw_post_data
	response = HttpResponse(data, mimetype='image/png')
	response['Content-Disposition'] = 'attachment; filename=image.png'
	return response


def pdf(request):
	data = request.raw_post_data
	# Create the HttpResponse object with the appropriate PDF headers.
	response = HttpResponse(data, mimetype='application/pdf')
	response['Content-Disposition'] = 'attachment; filename=image.pdf'
	return response

def sif(request):
	data = request.raw_post_data
	# Create the HttpResponse object with the appropriate PDF headers.
	response = HttpResponse(data, mimetype='text/plain')
	response['Content-Disposition'] = 'attachment; filename=graph.sif'
	return response

def graphml(request):
	data = request.raw_post_data
	# Create the HttpResponse object with the appropriate PDF headers.
	response = HttpResponse(data, mimetype='text/plain')
	response['Content-Disposition'] = 'attachment; filename=graph.graphml'
	return response


def download_metanets(request):

	def do_work():
		yield "\t".join(["MetaNet Name", "Gene Set 1 ID", "Gene Set 2 ID", "Gene Set 1 Name", "Gene Set 2 Name", "P-Value", "Benjamini P-Value"]) + "\n"
		for edge in MetaNetworkEdges.objects.all():
			metanet = MetaNetwork.objects.get(id=edge.network.id)
			term1 = GeneSet.objects.get(id=edge.term1.id)
			term2 = GeneSet.objects.get(id=edge.term2.id)

			yield	"\t".join([metanet.name, term1.id, term2.id, term1.name, term2.name, str(edge.pvalue), str(edge.benjamini)]) + "\n"

	return HttpResponse(do_work(), content_type="text/plain")
	
def download_genesets(request):

	def do_work():
		yield "\t".join(["Gene Set Collection", "Gene Set ID", "Gene Set Name", "Gene ID", "Gene Symbol"]) + "\n"
		for gs in GeneSet.objects.all():
			for member in gs.members.all():
				yield	"\t".join([gs.subgroup, gs.id, gs.name, str(member.id), member.symbol]) + "\n"

	return HttpResponse(do_work(), content_type="text/plain")


def download_results(request):
	global annotations, names, enrichment_results, gene_map

	genes = set(gene_map.keys())
	headers = ["Gene Set ID", "Gene Set Name", "Num. Genes in Input", "Num. Genes in Background", "Num. Genes in Gene Set", "Num. Genes in Gene Set and Input", "P-Value", "Benjamini Corrected P-Value", "List of Genes in Gene Set and Input"]
	data = []
	for result in enrichment_results:
		data.append([result["Annotation"], result["Name"], result["M"], result["N"], result["n"], result["m"], result["P-Value"], result["Benjamini P-Value"], str(sorted(result["Input Annotated"]))[1:-1]])
	
	#genesets = request.POST.getlist("genesets[]")
	#enrich_benjamini_cutoff = float(request.POST["benjamini"])
	
	t = loader.get_template("table_results.html")
	c = Context({
		"data": data,
		'headers': headers
	})
	return HttpResponse(t.render(c))



def geneset_members(request, geneset_id):
	members = set(GeneSet.objects.get(id=geneset_id).members.values_list("id", flat=True))
	data = []
	for member in members:
		data.append({"link": "http://www.ncbi.nlm.nih.gov/gene/%d" % member, "label": member})
	t = loader.get_template('link_list.html')
	c = Context({
		'data': data
	})
	return HttpResponse(t.render(c))	
   

	
def metanet(request):
	#t = loader.get_template("metanet2.html")
	t = loader.get_template("metanet_integrated.html")
	c = Context({
		"title": "METANET",
		"ajax_view": "PathVantage.metanet.views.ajax_metanet"
	})
	return HttpResponse(t.render(c))

def get_annots(geneset_family="KEGG"):
	subgroups = geneset_family.split("__")
	#subgroups = ["WikiPathways"]
	annotations = defaultdict(set)
	names = defaultdict(set)
	for subgroup in subgroups:
		if subgroup == "KEGG":
			subgroup = "KEGG PATHWAY"
		for geneset in GeneSet.objects.filter(subgroup=subgroup):
			annotations[geneset.id] = set(geneset.members.values_list("id", flat=True))
			names[geneset.id] = geneset.name
	return annotations, names

def ajax_enrichment(request, geneset_family="KEGG", gene_limit=1000, geneset_limit=50, pvalue_cutoff=1, corrected="uncorrected"):
	global annotations, names, enrichment_results, gene_map
	annotations = defaultdict(set)
	names = {}
	enrichment_results = []
	gene_map = defaultdict(set)

	genes = set([gene for gene in request.POST["genes"].strip().split("\n") if gene][:gene_limit])
	for gene in genes:
		try:
			gene_id = int(gene)
			gene_map[gene_id].add(Gene.objects.get(id=gene_id).symbol)
		except:
			try:
				gene_objs = Gene.objects.filter(symbol=gene.upper())
				for gene_obj in gene_objs:
					gene_map[gene_obj.id].add(gene)
			except:
				pass

	genes = set(gene_map.keys())
	
	geneset_family = request.POST["geneset_family"]
	pvalue_cutoff = float(request.POST["pvalue"])
	corrected = request.POST["corrected"]
	annotations, names = get_annots(geneset_family)
	results = enrichment.fishers(annotations, genes, alpha=pvalue_cutoff)
	enrichment_results = [] + results
	send_results = []
	if corrected == "uncorrected":
		field = "P-Value"
	elif corrected == "benjamini":
		field = "Benjamini P-Value"
	for result in results:
		if result[field] <= pvalue_cutoff:
			result["-log10 Benjamini P-Value"] = -1*log10(result["Benjamini P-Value"])
			result["Name"] = names[result["Annotation"]]
			result["Format Benjamini P-Value"] = "%0.3G" % result["Benjamini P-Value"]
			result["-log10 P-Value"] = -1*log10(result["P-Value"])
			result["Format P-Value"] = "%0.3G" % result["P-Value"]
			send_results.append(result)

	send_results.sort(key=lambda x: x["Benjamini P-Value"])
	json = simplejson.dumps({"data": send_results[:geneset_limit]}, ensure_ascii=False)
	return HttpResponse(json, content_type = "application/json; charset=UTF-8")

def ajax_integrated_metanet(request, geneset_family="KEGG", metanet_benjamini_cutoff=0.05, metanet_pvalue_cutoff=1):
	global annotations, names, enrichment_results, gene_map
		
	results = request.POST

	genesets = results.getlist("genesets[]")
	geneset_family = request.POST["geneset_family"]
	#geneset_family = "WikiPathways"
	metanet_benjamini_cutoff = float(request.POST["benjamini"])
	metanet_types = results.getlist("metanet_types[]")
	genes = set(gene_map.keys())
	
	#make graph	   
	graph = ''
	root = etree.Element("graphml")
	key = etree.SubElement(root, "key", id="label")
	key.attrib["for"] = "all"
	key.attrib["attr.name"] = "label"
	key.attrib["attr.type"] = "string"

	key = etree.SubElement(root, "key", id="weight")
	key.attrib["for"] = "all"
	key.attrib["attr.name"] = "weight"
	key.attrib["attr.type"] = "double"

	key = etree.SubElement(root, "key", id="members")	
	key.attrib["for"] = "node"
	key.attrib["attr.name"] = "members"
	key.attrib["attr.type"] = "string"
	
	key = etree.SubElement(root, "key", id="node_shape")	
	key.attrib["for"] = "node"
	key.attrib["attr.name"] = "node_shape"
	key.attrib["attr.type"] = "string"
	
	key = etree.SubElement(root, "key", id="metanet_type")	
	key.attrib["for"] = "edge"
	key.attrib["attr.name"] = "metanet_type"
	key.attrib["attr.type"] = "string"

	key = etree.SubElement(root, "key", id="edge_color")	
	key.attrib["for"] = "edge"
	key.attrib["attr.name"] = "edge_color"
	key.attrib["attr.type"] = "string"
	
	node_names = {}
	for node in genesets:
		node_names[node] = names[node]

	node_weights = {}
	for result in enrichment_results:
		node_weights[result["Annotation"]] = -1*log10(result["Benjamini P-Value"])
 
	#get co-membership edges
	all_edges = MetaNetworkEdges.objects.filter(network__id=geneset_family+" comembership", benjamini__lte=metanet_benjamini_cutoff)
	#get neighbors
	neighbors = defaultdict(set)
	comem_edges = []
	for edge in all_edges.filter(term1__id__in=genesets, term2__id__in=genesets):
		comem_edges.append(edge) 
		neighbors[edge.term1.id].add(edge.term2.id)
		neighbors[edge.term2.id].add(edge.term1.id)

	#check for dependence: if there are more genes that are unique than shared, then still enriched
	dependent = {}
	for node in node_names:
		#get neighbors
		nbors = neighbors[node]
		greater_shared = False
		for nbor in node_names:
			if node == nbor:
				continue
			#check if unique are less than shared
			if len(genes & (annotations[node] - annotations[nbor])) < len(genes & (annotations[node] & annotations[nbor])):
				greater_shared = True
				break
		
		dependent[node] = greater_shared

	graph = etree.SubElement(root, "graph")
	graph.attrib['edgedefault'] = "undirected"
	#add nodes
	for node_id in node_names:
		node_name = node_names[node_id]
		node = etree.SubElement(graph, "node")
		node.attrib['id'] = str(node_id)
		data = etree.SubElement(node, "data", key="label") 
		data.text=str(node_name)
		data = etree.SubElement(node, "data", key="weight")
		data.text=str(25 + node_weights[node_id])	
		data = etree.SubElement(node, "data", key="members")
		node_genes = set()
		for gene in genes & annotations[node_id]:
			node_genes |= set(["<a href='http://www.ncbi.nlm.nih.gov/gene/%d' target='_blank'>%s</a>" % (gene, val) for val in gene_map[gene]])
		data.text= str(", ".join(sorted(node_genes))) 
		data = etree.SubElement(node, "data", key="node_shape") 
		if dependent[node_id]:
			data.text = "ELLIPSE"
		else:
			data.text = "DIAMOND"

		
			
	#add edges
	for metanet_type in metanet_types:
		if metanet_type == "comembership":
			edges = [] + comem_edges
		
			#add edges
			for edge in edges:
				n1, n2 = (edge.term1.id, edge.term2.id)
				graph_edge = etree.SubElement(graph, "edge", source=str(n1), target=str(n2))
				data = etree.SubElement(graph_edge, "data", key="weight")
				data.text=str(-1*log10(edge.benjamini))	 
				data = etree.SubElement(graph_edge, "data", key="metanet_type")
				data.text=str(metanet_type) 
				data = etree.SubElement(graph_edge, "data", key="edge_color")
				data.text=str("#000000")	
				
		if metanet_type == "coenrichment_de":
			all_edges = MetaNetworkEdges.objects.filter(network__id=geneset_family+" coenrichment_differential_expression", benjamini__lte=metanet_benjamini_cutoff)
			edges = []

			for edge in all_edges.filter(term1__id__in=genesets, term2__id__in=genesets):
				edges.append(edge)
		
			#add edges
			for edge in edges:
				n1, n2 = (edge.term1.id, edge.term2.id)
				graph_edge = etree.SubElement(graph, "edge", source=str(n1), target=str(n2))
				data = etree.SubElement(graph_edge, "data", key="weight")
				data.text=str(-1*log10(edge.benjamini))	 
				data = etree.SubElement(graph_edge, "data", key="metanet_type")
				data.text=str(metanet_type) 
				data = etree.SubElement(graph_edge, "data", key="edge_color")
				data.text=str("#006633")	

		if metanet_type == "linkage_ppi":
			all_edges = MetaNetworkEdges.objects.filter(network__id=geneset_family+" linkage_ppi", benjamini__lte=metanet_benjamini_cutoff)
			edges = []

			for edge in all_edges.filter(term1__id__in=genesets, term2__id__in=genesets):
				edges.append(edge)
		
			#add edges
			for edge in edges:
				n1, n2 = (edge.term1.id, edge.term2.id)
				graph_edge = etree.SubElement(graph, "edge", source=str(n1), target=str(n2))
				data = etree.SubElement(graph_edge, "data", key="weight")
				data.text=str(-1*log10(edge.benjamini))	 
				data = etree.SubElement(graph_edge, "data", key="metanet_type")
				data.text=str(metanet_type) 
				data = etree.SubElement(graph_edge, "data", key="edge_color")
				data.text=str("#6600CC")			

  
	graph = str(etree.tostring(root))
	id = "integrated_metanet"
	rdict = {"data": graph, "id":id}
	json = simplejson.dumps(rdict, ensure_ascii=False)
	return HttpResponse(json, content_type = "application/json; charset=UTF-8")



