import lxml.etree as etree
import subprocess
import tempfile
import time
import psutil
import os
import numpy as np
from shapely.wkt import loads

from snappy import GPF

class GraphProcessor():
    
    def __init__(self, wdir='.'):
        self.root = etree.Element('graph')
    
        version = etree.SubElement(self.root, 'version')
        version.text = '1.0'
        self.pid = None
        self.p = None
        self.wdir = wdir
   
    def view_graph(self):
        
        print etree.tostring(self.root , pretty_print=True)
        
    def add_node(self, node_id, operator, parameters, source):
    
        xpath_expr = '/graph/node[@id="%s"]' % node_id

        if len(self.root.xpath(xpath_expr)) != 0:

            node_elem = self.root.xpath(xpath_expr)[0]
            operator_elem = self.root.xpath(xpath_expr + '/operator')[0]
            sources_elem = self.root.xpath(xpath_expr + '/sources')[0]
            parameters_elem = self.root.xpath(xpath_expr + '/parameters')

            for key, value in parameters.iteritems():
                
                if key == 'targetBandDescriptors':
                                        
                    parameters_elem.append(etree.fromstring(value))
                    
                else:
                    p_elem = self.root.xpath(xpath_expr + '/parameters/%s' % key)[0]

                    if value is not None:             
                        if value[0] != '<':
                            p_elem.text = value
                        else:
                            p_elem.text.append(etree.fromstring(value))
    
        else:

            node_elem = etree.SubElement(self.root, 'node')
            operator_elem = etree.SubElement(node_elem, 'operator')
            sources_elem = etree.SubElement(node_elem, 'sources')

            if isinstance(source, list):

                for index, s in enumerate(source):
                    if index == 0:  
                        source_product_elem = etree.SubElement(sources_elem, 'sourceProduct')

                    else: 
                        source_product_elem = etree.SubElement(sources_elem, 'sourceProduct.%s' % str(index))

                    source_product_elem.attrib['refid'] = s

            elif source != '':
                source_product_elem = etree.SubElement(sources_elem, 'sourceProduct')
                source_product_elem.attrib['refid'] = source

            parameters_elem = etree.SubElement(node_elem, 'parameters')
            parameters_elem.attrib['class'] = 'com.bc.ceres.binding.dom.XppDomElement'

            for key, value in parameters.iteritems():

                if key == 'targetBandDescriptors':
                                        
                    parameters_elem.append(etree.fromstring(value))
                    
                else:
                
                    parameter_elem = etree.SubElement(parameters_elem, key)

                    if value is not None:             
                        if value[0] != '<':
                            parameter_elem.text = value
                        else:
                            parameter_elem.append(etree.fromstring(value))

        node_elem.attrib['id'] = node_id

        operator_elem.text = operator 

    def save_graph(self, filename):
        
        with open(filename, 'wb') as file:
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write(etree.tostring(self.root, pretty_print=True))
     
    def plot_graph(self):
        
        for node_id in self.root.xpath('/graph/node/@id'):
            

            xpath_expr = '/graph/node[@id="%s"]' % node_id
            
            if len(self.root.xpath(xpath_expr + '/sources/sourceProduct')) != 0:
                print(self.root.xpath(xpath_expr + '/sources/sourceProduct'))[0].attrib['refid']
                print node_id
            else:
                print node_id
        return True
    
    def run(self):
        
        os.environ['LD_LIBRARY_PATH'] = '.'
        
        print 'Processing the graph'
        
        fd, path = tempfile.mkstemp()
        
        try:
        
            self.save_graph(filename=path)
            options = ['/opt/snap/bin/gpt',
               '-x',
               '-c',
               '2048M',
               path]

            p = subprocess.Popen(options,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

            print 'Process PID: %s' % p.pid
            res, err = p.communicate()
            print res, err
        finally:
            os.remove(path)
            
            print 'Done.'
        
def get_snap_parameters(operator):
    
    op_spi = GPF.getDefaultInstance().getOperatorSpiRegistry().getOperatorSpi(operator)

    op_params = op_spi.getOperatorDescriptor().getParameterDescriptors()

    return op_params

def get_operator_default_parameters(operator):
    
    parameters = dict()

    for param in get_snap_parameters(operator):
    
        parameters[param.getName()] = param.getDefaultValue()
    
    return parameters

def create_metadata(metadata, filename):

    namespaces = dict()

    namespaces['opt'] = 'http://www.opengis.net/opt/2.1'
    namespaces['om']  = 'http://www.opengis.net/om/2.0'
    namespaces['gml'] = 'http://www.opengis.net/gml/3.2'
    namespaces['eop'] = 'http://www.opengis.net/eop/2.1'
    namespaces['sar'] = 'http://www.opengis.net/sar/2.1'
    namespaces['ssp'] = 'http://www.opengis.net/ssp/2.1'
    
    
    for key, value in namespaces.items():
        etree.register_namespace(key, value)
   
    root = etree.Element('{{}}EarthObservation'.format(namespaces['ssp']))

    # Time
    if 'startdate' in metadata.keys():
    
        phenomenon_time = etree.SubElement(root, '{{{}}}phenomenonTime'.format(namespaces['om']))
        time_period = etree.SubElement(phenomenon_time, '{{{}}}TimePeriod'.format(namespaces['gml']))
        begin_position = etree.SubElement(time_period, '{{{}}}beginPosition'.format(namespaces['gml']))
        end_position = etree.SubElement(time_period, '{{{}}}endPosition'.format(namespaces['gml']))
    
        begin_position.text = metadata['startdate']
        end_position.text = metadata['enddate']
    
    # geo
    if 'wkt' in metadata.keys():
        
        feature_of_interest = etree.SubElement(root, '{{{}}}featureOfInterest'.format(namespaces['om']))
        footprint = etree.SubElement(feature_of_interest, '{{{}}}Footprint'.format(namespaces['ssp']))
        multi_extentOf = etree.SubElement(footprint, '{{{}}}multiExtentOf'.format(namespaces['ssp']))
        multi_surface = etree.SubElement(multi_extentOf, '{{{}}}MultiSurface'.format(namespaces['gml']))
        surface_members = etree.SubElement(multi_surface, '{{{}}}surfaceMembers'.format(namespaces['gml']))
        polygon = etree.SubElement(surface_members, '{{{}}}Polygon'.format(namespaces['gml']))
        exterior = etree.SubElement(polygon, '{{{}}}exterior'.format(namespaces['gml']))
        linear_ring = etree.SubElement(exterior, '{{{}}}LinearRing'.format(namespaces['gml']))
        poslist = etree.SubElement(linear_ring, '{{{}}}posList'.format(namespaces['gml']))
        
        
        coords = np.asarray([t[::-1] for t in list(loads(metadata['wkt']).exterior.coords)]).tolist()
 
        pos_list = ''
        for elem in coords:
            pos_list += ' '.join(str(e) for e in elem) + ' '   

        poslist.attrib['count'] = str(len(coords))
        poslist.text = pos_list


    if 'product_type' in metadata.keys():
   
        # Metadata property
        metadata_property = etree.SubElement(root, '{{{}}}metaDataProperty'.format(namespaces['eop']))
        earth_observation_metadata = etree.SubElement(metadata_property, '{{{}}}EarthObservationMetaData'.format(namespaces['eop']))
        identifier = etree.SubElement(earth_observation_metadata, '{{{}}}identifier'.format(namespaces['eop']))
        product_type = etree.SubElement(earth_observation_metadata, '{{{}}}productType'.format(namespaces['eop']))
        identifier.text = metadata['identifier'] 
        product_type.text = metadata['product_type'] 

    if 'vs' in metadata.keys():
        
        if not 'product_type' in metadata.keys():
            
            metadata_property = etree.SubElement(root, '{{{}}}metaDataProperty'.format(namespaces['eop']))
            earth_observation_metadata = etree.SubElement(metadata_property, '{{{}}}EarthObservationMetaData'.format(namespaces['eop']))
   
        vendor_specific = etree.SubElement(earth_observation_metadata, '{{{}}}vendorSpecific'.format(namespaces['eop']))
    
        for k, v in vs.items():
       
            specific_information = etree.SubElement(vendor_specific, '{{{}}}SpecificInformation'.format(namespaces['eop']))
            local_attribute = etree.SubElement(specific_information, '{{{}}}localAttribute'.format(namespaces['eop']))
            local_value = etree.SubElement(specific_information, '{{{}}}localValue'.format(namespaces['eop']))

            local_attribute.text = k
            local_value.text = v
    
   
            
    eop_xml = filename + '.xml'
    with open(eop_xml, 'wb') as file:
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write(etree.tostring(root, pretty_print=True))
    
    with open(filename + '.properties', 'wb') as file:

        if 'title' in metadata.keys():
            file.write('title={}\n'.format(metadata['title']))

        if 'startdate' and 'enddate' in metadata.keys():
            file.write('date={}/{}\n'.format(metadata['startdate'], 
                                             metadata['enddate']))

        if 'wkt' in metadata.keys():
            file.write('geometry={0}\n'.format(metadata['wkt']))

        if 'cat' in metadata.keys():
            
            temp_expression = []
            for k, v in cat.items():

                temp_expression.append(','.join(metadata['cat'][k].values()))

            cat_expression = '|'.join(temp_expression)
            
            file.write('category={}'.format(cat_expression))

    return filename + '.xml', filename + '.properties'

