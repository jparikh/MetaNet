// JavaScript Document

//cytoscape


function draw_net(id, data, node_click_function, edge_click_function){
    var net_xml;
    // initialization options
    var swf_options = {
        swfPath: "./media/cytoscapeweb_v0.8/swf/CytoscapeWeb",
        flashInstallerPath: "./media/cytoscapeweb_v0.8/swf/playerProductInstall"
    };
    var visual_style;
    // visual style we will use
    visual_style = {
        global: {
            backgroundColor: "#FFFFFF"
        },
        nodes: {
            shape: {
            	defaultValue: "ELLIPSE",
            	passthroughMapper: { attrName: "node_shape" }
            },
            borderWidth: 2,
            borderColor: "#DDDDDD",
            size: {
                defaultValue: 50,
                continuousMapper: { attrName: "weight", minValue: 25, maxValue: 75 }
            },
            color: "#7F181A",
            labelHorizontalAnchor: "center",
            labelFontSize: 18,
            labelFontWeight : "regular",
            labelFontColor: "#FFFFFF",
            labelVerticalAnchor: "top",
            labelGlowColor: "#333333",
            labelGlowOpacity: 1,
            labelGlowBlur: 4
        },
        edges: {
            width: {
                defaultValue: 4,
            },
            //color: "#888888",
            color: {
            	defaultValue: "#888888",
            	opacity: 0.2,
            	passthroughMapper: { attrName: "edge_color" }
            },
            curvature: 25,
            sourceArrowShape: {
            	defaultValue: "NONE",
            	passthroughMapper: { attrName: "source_arrow" }
            },
            targetArrowShape: {
            	defaultValue: "NONE",
            	passthroughMapper: { attrName: "target_arrow" }
            }
        }
    };
    
    var bypass = { nodes: { }, edges: { } };
    
    var layout;
    layout = {
        name: "ForceDirected",
        options: { gravitation: -8000 }
    };
    var draw_options;

    var vis = new org.cytoscapeweb.Visualization(id+"_cytonet", swf_options);

    //menubar
                
    $("#"+id).append("<div id='" + id + "_menu'>\
        &nbsp;&nbsp;<a class='hoverText' id='" + id + "_menu_legend'>Legend</a>\
        &nbsp;&nbsp;<a class='hoverText' id='" + id + "_menu_nodes'>Nodes</a>\
        &nbsp;&nbsp;<a class='hoverText' id='" + id + "_menu_edges'>Edges</a>\
        &nbsp;&nbsp;<a class='hoverText' id='" + id + "_menu_layout'>Layout</a>\
        &nbsp;&nbsp;<a class='hoverText' id='" + id + "_menu_save'>Save</a>\
        </div>")
        
    //create dialogs
    //Legend
    $("#"+id).append("<div id='" + id + "_menu_legend_options' name='" + id + "_menu_legend_options'>\
		<object data='./media/images/metanet_legend.svg' type='image/svg+xml' width='250'></object>\
        </div>");
        
    $( "#"+id+"_menu_legend_options" ).dialog({
    		dialogClass: "ui-dialog-legend",
  			autoOpen: false,
  			modal: false,
  			resizable: false,
  			width: 260,
  			close: function(event, ui) {legend_open=false;}
    });	
		    
    $("#"+id+"_menu_legend").click(function() {
		var position =  $("#"+id+"_menu").offset();
		$("#"+id+"_menu_legend_options").dialog("option", "position", [position.left, position.top + 25]);
		$("#"+id+"_menu_legend_options").dialog('open');
		legend_open = true;
    });
        
    
    //nodes
    $("#"+id).append("<div id='" + id + "_menu_node_options' name='" + id + "_menu_node_options' title='Node Options' height=60% width=60%>\
        Enter node size: \
            <input type='text' id='" + id + "_menu_node_options_size' value='50'/><br>\
        Select node shape: \
            <select id='" + id + "_menu_node_options_shape' name='" + id + "_menu_node_options_shape'>\
                <option value='ELLIPSE' selected>Circle</option>\
                <option value='RECTANGLE'>Rectangle</option>\
                <option value='TRIANGLE'>Triangle</option>\
                <option value='DIAMOND'>Diamond</option>\
                <option value='HEXAGON'>Hexagon</option>\
                <option value='OCTAGON'>Octagon</option>\
                <option value='PARALLELOGRAM'>Parallelogram</option>\
                <option value='ROUNDRECT'>Roundrect</option>\
                <option value='VEE'>Vee</option>\
            </select><br>\
        <div><label for='" + id + "_menu_node_options_color'>Select node color:</label>\
            <input type='text' id='" + id + "_menu_node_options_color' value='#7F181A'/></div><br>\
        </div>");
    
    
    $( "#"+id+"_menu_node_options" ).dialog({
  			autoOpen: false,
  			modal: false,
  			buttons: {
  			   Default: function() {
  			       $( "#"+id+"_menu_node_options_size" ).val( "50" );
  			       $( "#"+id+"_menu_node_options_shape" ).val("ELLIPSE");
  			       $( "#"+id+"_menu_node_options_color" ).val("#7F181A");
  			       $( "#"+id+"_menu_node_options_color" ).change();
  			   },
  			   "Set Options": function() {
    		       $.each( vis.selected("nodes"), function(index, node) {
                  bypass["nodes"][node.data.id] = {
                      size: $( "#"+id+"_menu_node_options_size" ).val(),
                      shape: $( "#"+id+"_menu_node_options_shape" ).val(),
                      color: $( "#"+id+"_menu_node_options_color" ).val(),
                  };
               });
               vis.visualStyleBypass(bypass);
               $( "#"+id+"_menu_node_options" ).dialog( "close" );
  			   }
  			},
    });	
		    
    $("#"+id+"_menu_nodes").click(function() {
        $( "#"+id+"_menu_node_options" ).dialog( "open" );
    });
    
    $("#"+id+"_menu_node_options_color").colorPicker();
    
    //edges
    $("#"+id).append("<div id='" + id + "_menu_edge_options' name='" + id + "_menu_edge_options' title='Edge Options' height=60% width=60%>\
        Enter edge width: \
            <input type='text' id='" + id + "_menu_edge_options_size' value='2'/><br>\
        Select edge target arrow shape: \
            <select id='" + id + "_menu_edge_options_shape' name='" + id + "_menu_edge_options_shape'>\
                <option value='NONE' selected>None</option>\
                <option value='DELTA'>Delta</option>\
                <option value='ARROW'>Arrow</option>\
                <option value='DIAMOND'>Diamond</option>\
                <option value='CIRCLE'>Circle</option>\
                <option value='T'>T</option>\
            </select><br>\
        <div><label for='" + id + "_menu_edge_options_color'>Select edge color:</label>\
            <input type='text' id='" + id + "_menu_edge_options_color' value='#888888'/></div><br>\
        </div>");
        
    $( "#"+id+"_menu_edge_options" ).dialog({
        zIndex: z_index,
  			autoOpen: false,
  			modal: true,
  			buttons: {
  			   Default: function() {
  			       $( "#"+id+"_menu_edge_options_size" ).val( "2" );
  			       $( "#"+id+"_menu_edge_options_shape" ).val("NONE");
  			       $( "#"+id+"_menu_edge_options_color" ).val("#888888");
  			       $( "#"+id+"_menu_edge_options_color" ).change();
  			   },
  			   "Set Options": function() {
    		       $.each( vis.selected("edges"), function(index, edge) {
                  bypass["edges"][edge.data.id] = {
                      width: $( "#"+id+"_menu_edge_options_size" ).val(),
                      targetArrowShape: $( "#"+id+"_menu_edge_options_shape" ).val(),
                      color: $( "#"+id+"_menu_edge_options_color" ).val(),
                  };
               });
               vis.visualStyleBypass(bypass);
               $( "#"+id+"_menu_edge_options" ).dialog( "close" );
  			   }
  			},
    });	
		    
    $("#"+id+"_menu_edges").click(function() {
        $( "#"+id+"_menu_edge_options" ).dialog( "open" );
    });
    
    $("#"+id+"_menu_edge_options_color").colorPicker();
    
    
    //Layout
    $("#"+id).append("<div id='" + id + "_menu_layout_options' name='" + id + "_menu_layout_options' title='Edge Options' height=60% width=60%>\
        Select layout: \
            <select id='" + id + "_menu_layout_options_name' name='" + id + "_menu_layout_options_name'>\
                <option value='ForceDirected' selected>Force Directed</option>\
                <option value='Circle'>Circle</option>\
                <option value='Radial'>Radial</option>\
                <option value='Tree'>Tree</option>\
            </select><br>\
        </div>");
        
    $( "#"+id+"_menu_layout_options" ).dialog({
        zIndex: z_index,
  			autoOpen: false,
  			modal: true,
  			buttons: {
  			   Default: function() {
  			       $( "#"+id+"_menu_layout_options_name" ).val( "ForceDirected" );
  			   },
  			   "Set Options": function() {
    		       layout["name"] = $( "#"+id+"_menu_layout_options_name" ).val();
               vis.layout(layout);
               vis.select();
               vis.deselect();
               $( "#"+id+"_menu_layout_options" ).dialog( "close" );
  			   }
  			},
    });	
		    
    $("#"+id+"_menu_layout").click(function() {
        $( "#"+id+"_menu_layout_options" ).dialog( "open" );
    });
    
    
    //Save
    $("#"+id).append("<div id='" + id + "_menu_save_options' name='" + id + "_menu_save_options' title='Save Options' height=60% width=60%>\
        Select layout: \
            <select id='" + id + "_menu_save_options_type' name='" + id + "_menu_save_options_type'>\
                <option value='png' selected>PNG</option>\
                <option value='pdf'>PDF</option>\
                <option value='sif'>SIF</option>\
                <option value='graphml'>GraphML</option>\
            </select><br>\
        </div>");
        
    $( "#"+id+"_menu_save_options" ).dialog({
        zIndex: z_index,
  			autoOpen: false,
  			modal: true,
  			buttons: {
            OK: function() {
                var file_type = $( "#"+id+"_menu_save_options_type" ).val();
                vis.exportNetwork(file_type, "/" + file_type + "/", { nodeAttr: 'label', interactionAttr: 'metanet_type'})
                $( "#"+id+"_menu_save_options" ).dialog( "close" );
  			   }
  			},
    });	
		    
    $("#"+id+"_menu_save").click(function() {
        $( "#"+id+"_menu_save_options" ).dialog( "open" );
    });
    
  
    //cytoscape network
    $("#"+id).append("<div id='" + id + "_cytonet'></div>")
    $("#"+id+"_cytonet").height("100%")
    
      // callback when Cytoscape Web has finished drawing
    vis.ready(function() {
        // add a listener for when nodes and edges are clicked
        vis.addListener("click", "nodes", function(event) {
            node_click_function(event);
        });
        vis.addListener("click", "edges", function(event) {
            edge_click_function(event);
        });
        
    });

      
    draw_options = {
        // your data goes here
        network: data,
        
        // show edge labels too
        nodeLabelsVisible: true,
        
        // let's try another layout
        layout: layout,
        
        // set the style at initialisation
        visualStyle: visual_style,
        
        // hide pan zoom
        panZoomControlVisible: true, 
        panZoomControlPosition: "topRight",

    };
  
    vis.draw(draw_options);
};