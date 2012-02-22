from django.conf.urls.defaults import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
	# Examples:
	# url(r'^$', 'metanet.views.home', name='home'),
	# url(r'^metanet/', include('metanet.foo.urls')),

	# Uncomment the admin/doc line below to enable admin documentation:
	# url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

	# Uncomment the next line to enable the admin:
	# url(r'^admin/', include(admin.site.urls)),
	
	#media
	(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT }),

					   
	(r'^png/', 'metanet.webapp.views.png'),
	(r'^pdf/', 'metanet.webapp.views.pdf'),					   
	(r'^sif/', 'metanet.webapp.views.sif'),										  
	(r'^graphml/', 'metanet.webapp.views.graphml'),					   

	url(r'^$', 'metanet.webapp.views.metanet'), 
	url(r'^ajax_enrichment/$', 'metanet.webapp.views.ajax_enrichment'),	   
	url(r'^ajax_integrated_metanet/$', 'metanet.webapp.views.ajax_integrated_metanet'),	   
	url(r'^download_results/$', 'metanet.webapp.views.download_results'),
	url(r'^download_metanets/$', 'metanet.webapp.views.download_metanets'),
	url(r'^download_genesets/$', 'metanet.webapp.views.download_genesets'),
	url(r'^geneset/(?P<geneset_id>.+)/$', 'metanet.webapp.views.geneset_members'),
	
)
