import datetime
from pytz import timezone
import numpy
import logging
import sys
import argparse
import pkg_resources
import yaml

standard_name_file = pkg_resources.resource_filename('pycnv', 'rules/standard_names.yaml')

# Get the version
version_file = pkg_resources.resource_filename('pycnv','VERSION')

with open(version_file) as version_f:
   version = version_f.read().strip()

# TODO: add NMEA position, time

# Setup logging module
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
logger = logging.getLogger('pycnv')

# Regions to test if we are in the Baltic Sea for different equation of state
regions_baltic = []
regions_baltic.append([[ 10.2,  13. ],[ 56.2,  57.5]])
regions_baltic.append([[  9.4,  13.4],[ 53.9,  56.3]])
regions_baltic.append([[ 13.3,  17.],[ 53.4,  56.3]])
regions_baltic.append([[ 15.9,  24.6],[ 54.2,  60.2 ]])
regions_baltic.append([[ 24.3,  30.4],[ 59.1,  60.8]])
regions_baltic.append([[ 16.8,  23.3],[ 60.1,  63.3]])
regions_baltic.append([[ 18.8,  25.6],[ 63.1,  66.2]])

def check_baltic(lon,lat):
    """
    Functions checks if position with lon,lat is in the Baltic Sea
    Args:
       lon: Longitude
       lat: Latitude
    Returns:
       baltic: True: In Baltic, False: not in Baltic
    """
    if(lon == None or lon == numpy.NaN or lat == None or lat == numpy.NaN):
        return False
    
    for i in range(len(regions_baltic)):
        lonb = regions_baltic[i][0]
        latb = regions_baltic[i][1]
        if((lon > lonb[0]) and (lon < lonb[1])):
            if((lat > latb[0]) and (lat < latb[1])):
                return True

    return False


try:
    import gsw
except:
    logger.warning('Could not load the Gibbs Seawater toolbox')



def date_correction(tag, monat, jahr):
    """
    @author: Robert Mars, IOW
    modified and improved by Peter Holtermann, IOW
    """
    
    ### Vereinheitlichung des Datums nach ISO
    # German month naming
    if monat.lower()=="dez": monat_int = 12
    if monat.lower()=="mrz": monat_int = 3        
    if monat.lower()=="mai": monat_int = 5
    if monat.lower()=="okt": monat_int = 10    
    if monat.lower()=="jan": monat_int = 1
    if monat.lower()=="feb": monat_int = 2
    if monat.lower()=="mar": monat_int = 3
    if monat.lower()=="apr": monat_int = 4
    if monat.lower()=="may": monat_int = 5
    if monat.lower()=="jun" :monat_int = 6
    if monat.lower()=="jul": monat_int = 7
    if monat.lower()=="aug": monat_int = 8
    if monat.lower()=="sep": monat_int = 9
    if monat.lower()=="oct": monat_int = 10
    if monat.lower()=="nov": monat_int = 11
    if monat.lower()=="dec": monat_int = 12

    # print ("day: %s| month: %s| year: %s " % (cal[0],cal[1],cal[2]))
    # print ("date: %s" % datetime.date(cal_year,cal_month,cal_day))
    try:
        datstr = datetime.date(int(jahr),int(monat_int),int(tag)).isoformat()
        return datstr
    except Exception as e:
        logger.warning(' Could not convert date: ' + str(e))
        return None    


def parse_iow_header(header):
    """
    Parsing the header for iow_data and saving it into a structure
    """
    iow_data = {}
    for line in header.splitlines():
        #print line
        if  "Startzeit" in line:
            # This can happen
            # ** Startzeit= 13:13:15 25-Sep-07
            # ** Startzeit= 07:13:09 utc 28-APR-99
            line_orig = line
            line = line.replace('UTC','')
            line = line.replace('utc','')            
            #print(line)
            try:
                line = line.replace("\n","").replace("\r","")
                line = line.split("=")     
                line = line[1]
                line = line.replace("  "," ")
                while(line[0] == " "):
                    line = line[1:]

                line_split = line.split(" ")
                # Get datum
                datum_split = line_split[1].split("-")
                tag = datum_split[0]
                monat = datum_split[1]            
                jahr = datum_split[2]
                if(len(jahr) == 2):
                    if(int(jahr) < 80): # 2000 - 2079
                        jahr = '20' + jahr
                    else: # 1980-1999
                        jahr = '19' + jahr                    

                #print(line)
                datum_start = date_correction(tag, monat, jahr)


                # get time
                zeit_start = line_split[0]
                try:
                    iow_data['date'] = datetime.datetime.strptime(datum_start + zeit_start,'%Y-%m-%d%H:%M:%S')
                    iow_data['date'].replace(tzinfo=timezone('UTC'))
                except:
                    logger.warning('Startzeit to datetime:' + str(e))
                    logger.warning('Startzeit str:' + line_orig)                    
                    iow_data['date'] = None
                    
            except Exception as e:
                logger.warning('Startzeit parsing error:' + str(e))
                logger.warning('Startzeit str:' + line_orig)


        ###### Meta-Daten der Reise und Station
        elif "ReiseNr" in line:
            line = line.split("=")
            reise = line[1]
            reise = reise.replace(" ","")
            reise = reise.replace("\n","").replace("\r","")
            iow_data['reise'] = reise
            # print("Reise: %s" % reise)
        elif "StatBez" in line:
            line = line.split("=")
            station_bez = line[1]
            # station_bez = station_bez.replace(" ","")
            station_bez = station_bez.replace("\n","").replace("\r","")
            iow_data['station'] = station_bez
            # print("Station: %s" % station_bez)
        elif "EinsatzNr" in line:
            line = line.split("=")
            einsatz_nr = line[1]
            einsatz_nr = einsatz_nr.replace(" ","")
            einsatz_nr = einsatz_nr.replace("\n","").replace("\r","")
            iow_data['einsatz'] = einsatz_nr
            # print("Einsatz: %s" % einsatz_nr)

        elif "Echolote" in line:

            line = line.split("=")
            try:
                echo0 = float(line[1].split('m')[0])
            except Exception as e:
                logger.debug('IOW:Echolot:' + str(e))
                echo0 = None

            try:
                echo1 = float(line[1].split('m')[1])
            except Exception as e:
                logger.debug('IOW:Echolot:' + str(e))
                echo1 = None                

            iow_data['echo'] = (echo0,echo1)
                
            # print("Einsatz: %s" % einsatz_nr)            
        elif "SerieNr" in line and "Operator" in line:
            line_orig = line
            line.replace("\n","").replace("\r","")
            line = line.split()
            try:
                serie_nr = line[3]
            except Exception as e:
                logger.debug('SerieNr parsing error:' + str(e))
                logger.debug('str:' + line_orig)
                serie_nr = ''

            try:                
                operator = line[5]
            except Exception as e:
                logger.debug('Operator parsing error:' + str(e))
                logger.debug('str:' + line_orig)
                operator = ''                

            # print("Serie: %s" % serie_nr)
            # print("Operator: %s" % operator)
            iow_data['serie'] = serie_nr
            iow_data['operator'] = operator
        elif "GPS_Posn" in line:
            try:

                pos_str = line.rsplit('=')[1]
                pos_str = pos_str.replace("\n","").replace("\r","") 
                if("S" in pos_str):
                    SIGN_NORTH = -1.
                    CHAR_NORTH = 'S'
                if("N" in pos_str):
                    SIGN_NORTH = 1.
                    CHAR_NORTH = 'N'                

                if("E" in pos_str):
                    SIGN_WEST = 1.0
                    CHAR_WEST = 'E'
                if("W" in pos_str):
                    SIGN_WEST = -1.0
                    CHAR_WEST = 'W'

                pos_str = pos_str.replace("N","")
                pos_str = pos_str.replace("S","")
                pos_str = pos_str.replace("E","")
                pos_str = pos_str.replace("W","")
                pos_str = pos_str.replace("  "," ")
                pos_str = pos_str.split()
                while(pos_str[0] == " "):
                        pos_str = pos_str[1:]


                latitude = ("%s %s" % (pos_str[0],pos_str[1]))
                longitude = ("%s %s" % (pos_str[2],pos_str[3]))
                latitude += CHAR_NORTH
                longitude += CHAR_WEST
                # Convert to floats
                lon = SIGN_WEST * float(longitude.split()[0]) + float(longitude.split()[1][:-1])/60.
                lat = SIGN_NORTH * float(latitude.split()[0]) + float(latitude.split()[1][:-1])/60.

            except Exception as e:
                logger.warning('Could not get a valid position, setting it to unknown:' + str(e))
                logger.warning('str:' + line)
                logger.warning('pos str:' + str(pos_str))
                latitude = 'unknown'
                longitude = 'unknown'
                lat = numpy.NaN
                lon = numpy.NaN
                
            iow_data['lat'] = lat
            iow_data['lon'] = lon

    return iow_data


class pycnv(object):
    """

    A Seabird cnv parsing object.

    Author: Peter Holtermann (peter.holtermann@io-warnemuende.de)

    Usage:
       >>>filename='test.cnv'
       >>>cnv = pycnv(filename)

    Args:
       filename:
       only_metadata:
       verbosity:
       naming_rules:
       encoding:
       baltic: Flag if the cast was in the Baltic Sea. None: Automatic check based on parsed lat/lon and the regions definded in pycnv.regions_baltic, True: cast is in Baltic, False: cast is not in Baltic. If cast is in Baltic the gsw equation of state for the Baltic Sea will be used.
    
    """
    def __init__(self,filename, only_metadata = False,verbosity = logging.INFO, naming_rules = standard_name_file,encoding='latin-1',baltic=None ):
        """
        """
        logger.setLevel(verbosity)
        logger.info(' Opening file: ' + filename)
        self.filename = filename
        self.file_type = ''
        self.channels = []
        self.data = None
        self.date = None        
        self.lon = numpy.NaN
        self.lat = numpy.NaN   
        # Opening file for read
        raw = open(self.filename, "r",encoding=encoding)
        #print('Hallo!',raw)
        # Find the header and store it
        header = self._get_header(raw)
        self._parse_header()
        # Check if we found channels
        # If yes we have a valid cnv file
        if(len(self.channels) == 0):
            logger.critical('Did not find any channels in file: ' + filename + ', exiting (No cnv file?)')
            self.valid_cnv = False
            return

        # Check if we have a known data format
        if 'ASCII' in self.file_type.upper():
            pass
        else:
            logger.critical('Data format in file: ' + filename + ', is ' + str(self.file_type) + ' which I cannot understand (right now).')
            self.valid_cnv = False
            return

        
        # Custom header information, at the moment only the IOW header
        # is supported, in future more headers should be added
        self.iow = parse_iow_header(self.header)
        try:
            self.lat = self.iow['lat']
            self.lon = self.iow['lon']
        except:
            pass

        # If no date was found, try the IOW date
        if self.date == None:
            try:
                self.date = self.iow['date']
            except:
                pass

            
            
        # Trying to extract standard names (p, C, S, T, oxy ... ) from the channel names
        self._get_standard_channel_names(naming_rules)

        self._get_data(raw)
        # Check if we are in the Baltic Sea
        if(baltic == None):
            self.baltic= check_baltic(self.lon,self.lat)
        else:
            self.baltic = baltic
            
        nrec           = numpy.shape(self.raw_data)[0]
        self.units     = {}
        self.names     = {}
        self.names_std = {}
        self.units_std = {}        
        # Check if the dimensions are right
        if(numpy.shape(self.raw_data)[0] > 0):
            if( numpy.shape(self.raw_data)[1] == len(self.channels) ):
                # Make a recarray out of the array
                names   = []
                formats = []
                titles  = []
                # Name the columns after the channel names
                for n,c in enumerate(self.channels):
                    names.append(c['name'])
                    formats.append('float')
                    titles.append(c['title'])
                    self.names[c['name']] = c['long_name']
                    self.units[c['name']] = c['unit']
                    self.names_std[c['title']] = c['long_name']
                    self.units_std[c['title']] = c['unit']
                    

                # Create a new recarray with the names as in the header as
                # the name and the standard names as the title
                self.data = numpy.zeros(numpy.shape(self.raw_data)[0],dtype={'names':names,'formats':formats,'titles':titles})
                # Fill the recarray
                #for n,c in enumerate(self.channels):
                for n in range(nrec):
                    self.data[n] = self.raw_data[n,:]

                self.data   = numpy.rec.array(self.data)
                # Compute absolute salinity and potential density with the gsw toolbox
                # check if we have enough data to compute
                self.cdata  = None
                self.cunits = {}
                self.cnames = {}
                try:
                    self.data['C0']
                    self.data['T0']
                    self.data['p']
                    FLAG_COMPUTE0 = True
                except:
                    FLAG_COMPUTE0 = False

                try:
                    self.data['C1']
                    self.data['T1']
                    self.data['p']
                    FLAG_COMPUTE1 = True
                except:
                    FLAG_COMPUTE1 = False                    

                if FLAG_COMPUTE0:
                    if(not((self.lon == numpy.NaN) or (self.lat == numpy.NaN))):
                        compdata    = self._compute_data(self.data, self.units_std, self.names_std, baltic=baltic,lon=self.lon, lat=self.lat,isen='0')
                    else:
                        compdata    = self._compute_data(self.data, self.units_std, self.names_std, baltic=baltic,isen = '0')


                    self.cdata = compdata[0]
                    self.cunits.update(compdata[1])
                    self.cnames.update(compdata[2])
                else:
                    logger.debug('Not computing data using the gsw toolbox, as we dont have the three standard parameters (C0,T0,p0)')

                if FLAG_COMPUTE1:
                    if(not((self.lon == numpy.NaN) or (self.lat == numpy.NaN))):
                        compdata    = self._compute_data(self.data, self.units_std, self.names_std, baltic=baltic,lon=self.lon, lat=self.lat,isen='1')
                    else:
                        compdata    = self._compute_data(self.data,self.units_std, self.names_std, baltic=baltic,isen = '0')
                    if self.cdata == None:
                        self.cdata = compdata[0]
                    else:
                        self.cdata.update(compdata[0])
                        
                    self.cunits.update(compdata[1])
                    self.cnames.update(compdata[2])
                else:
                    logger.debug('Not computing data using the gsw toolbox, as we dont have the three standard parameters (C1,T1,p)')
            else:
                logger.warning('Different number of columns in data section as defined in header, this is bad ...')
        else:
            logger.warning('No data in file')
            
            
        self.valid_cnv = True
        
        
    def _compute_data(self,data, units, names, p_ref = 0, baltic = False, lon=0, lat=0, isen = '0'):
        """ Computes convservative temperature, absolute salinity and potential density from input data, expects a recarray with the following entries data['C']: conductivity in mS/cm, data['T']: in Situ temperature in degree Celsius (ITS-90), data['p']: in situ sea pressure in dbar
        
        Arguments:
           p_ref: Reference pressure for potential density
           baltic: if True use the Baltic Sea density equation instead of open ocean
           lon: Longitude of ctd cast default=0
           lat: Latitude of ctd cast default=0
        Returns:
           list [cdata,cunits,cnames] with cdata: recarray with entries 'SP', 'SA', 'pot_rho', cunits: dictionary with units, cnames: dictionary with names 
        """
        sen = isen + isen
        # Check for units and convert them if neccessary
        if(units['C' + isen] == 'S/m'):
            logger.info('Converting conductivity units from S/m to mS/cm')
            Cfac = 10

        if(('68' in units['T' + isen]) or ('68' in names['T' + isen]) ):
            logger.info('Converting IPTS-68 to T90')
            T = gsw.t90_from_t68(data['T' + isen])
        else:
            T = data['T' + isen]
            
        SP = gsw.SP_from_C(data['C' + isen], T, data['p'])
        SA = gsw.SA_from_SP(SP,data['p'],lon = lon, lat = lat)
        if(baltic == True):
            SA = gsw.SA_from_SP_Baltic(SA,lon = lon, lat = lat)
            
        PT = gsw.pt0_from_t(SA, T, data['p'])
        CT = gsw.CT_from_t(SA, T, data['p'])        
        pot_rho          = gsw.pot_rho_t_exact(SA, T, data['p'], p_ref)
        names            = ['SP' + sen,'SA' + sen,'pot_rho' + sen,'pt0' + sen,'CT' + sen]
        formats          = ['float','float','float','float','float']        
        cdata            = {}
        cdata['SP' + sen]= SP
        cdata['SA' + sen]= SA
        cdata['pot_rho' + sen] = pot_rho
        cdata['pt0' + sen]     = PT
        cdata['CT' + sen]      = CT
        cnames           = {'SA' + sen:'Absolute salinity','SP' + sen: 'Practical Salinity on the PSS-78 scale',
                            'pot_rho' + sen: 'Potential density',
                            'pt0' + sen:'potential temperature with reference sea pressure (p_ref) = 0 dbar',
                            'CT' + sen:'Conservative Temperature (ITS-90)'}
       
        cunits = {'SA' + sen:'g/kg','SP' + sen:'PSU','pot_rho' + sen:'kg/m^3' ,'CT' + sen:'deg C','pt0' + sen:'deg C'}
        
        return [cdata,cunits,cnames]
    
    
    def _get_header(self,raw):
        """ Loops through lines and looks for header. It removes all \r leaving only \n for newline and saves the header in self.header as a string
        Args:
        Return:
            Line number of first data 
        """
        self.header = ''
        # Read line by line
        nline = 0
        for l in raw:
            nline +=1
            # removes all "\r", we only want "\n"
            l = l.replace("\r","")
            self.header += l
            if("*END*" in l):
                break
            # Check if we read more than 10000 lines and found nothing
            if(nline > 10000):
                self.header = ''
                break

        return nline

    
    def _parse_header(self):
        """
        Parses the header of the cnv file
        """
        for l in self.header.split('\n'):
            if "* System UpLoad Time" in l:
                line     = l.split(" = ")
                datum = line[1]
                try:
                    self.date = datetime.datetime.strptime(datum,'%b %d %Y %H:%M:%S')
                    self.date.replace(tzinfo=timezone('UTC'))
                except Exception as e:
                    logger.warning('Could not decode time: ( ' + datum + ' )' + str(e))

            # Look for sensor names and units of type:
            # # name 4 = t090C: Temperature [ITS-90, deg C]
            if "# name" in l:
                lsp = l.split("= ",1)
                sensor = {}
                sensor['index'] = int(lsp[0].split('name')[-1])
                sensor['name'] = lsp[1].split(': ')[0]
                # Test if we have already the name (no double names
                # are allowed later in the recarray struct
                for c,s in enumerate(self.channels):
                    if(s['name'] == sensor['name']):
                        sensor['name'] = sensor['name'] + '@' + str(c)

                # Add a dummy title, this will be later filled with a
                # useful name
                sensor['title'] = 'i' + str(sensor['index'])
                if(len(lsp[1].split(': ')) > 1): # if we have a long name and unit
                    sensor['long_name'] = lsp[1].split(': ')[1]
                    unit = lsp[1].split(': ')[1]
                    if len(unit.split('[')) > 1 :
                        unit = unit.split('[')[1]
                        unit = unit.split("]")[0]
                        sensor['unit'] = unit
                    else:
                        sensor['unit'] = None
                else:
                    sensor['long_name'] = None
                    sensor['unit'] = None

                self.channels.append(sensor)

            if "# file_type" in l:
                lsp = l.split("= ",1)
                file_type = lsp[1]
                file_type.replace(' ','')
                self.file_type = file_type
        
        
    def _get_standard_channel_names(self, naming_rules):
        """
        Look through a list of rules to try to link names to standard names
        """
        f = open(naming_rules)
        rules = yaml.safe_load(f)
        for r in rules['names']:
            found = False
            #logger.debug('Looking for rule for ' + r['description'])
            logger.debug('Looking for rule for ' + str(r['channels']) + '('+ r['description'] +')')            
            for c in r['channels']:
                if(found == True):
                    found = False
                    break
                for ct in self.channels:
                    if(ct['name'] in c):
                        ct['title'] = r['name']
                        logger.debug('Found channel' + str(ct) + ' ' + str(c))
                        found = True
                        break
    
        
        #print('Channels',self.channels)
        
    def _get_data(self,raw):
        """ Reads until the end of the file lines of data and puts them into one big numpy array
        """
        data = []
        nline = 0
        if True:
            for l in raw:
                line_orig = l
                l = l.replace("\n","").replace("\r","")
                l = l.split()
                #data.append (line)
                nline += 1
                try:
                    ldata = numpy.asarray(l,dtype='float')
                    # Get the number of columns with the first line
                    if(nline == 1):
                        ncols = len(ldata)

                    if(len(ldata) == ncols):
                        data.append(ldata)
                except Exception as e:
                    logger.warning('Could not convert data to floats in line:' + str(nline))
                    logger.debug('str:' + line_orig)

            
        self.raw_data = numpy.asarray(data)

    def get_summary(self,header=False):
        """
        Returns a summary of the cnv file in a csv format
        Args:
           header: Returns header only
        """
        
        sep = ','
        rstr = ""
        # Print the header
        if(header):
            rstr += 'Date' + sep
            rstr += 'Lat' + sep
            rstr += 'Lon' + sep
            rstr += 'p min' + sep
            rstr += 'p max' + sep
            rstr += 'num p samples' + sep
            rstr += 'baltic' + sep
            rstr += 'file'  + sep
        # Print the file information
        else:
            try:
                rstr += datetime.datetime.strftime(self.date,'%Y-%m-%d %H:%M:%S') + sep
            except: 
                rstr += 'NaN' + sep

            try:
                rstr += '{:03.5f}'.format(self.lat) + sep
                rstr += '{:03.5f}'.format(self.lon) + sep
                

            except:
                rstr += 'NaN' + sep
                rstr += 'NaN' + sep
            pmin = numpy.NaN
            pmax = numpy.NaN
            num_samples = 0                    
            if(self.data != None):
                #print(self.data)
                try:
                    pmin = self.data['p'].min()
                    pmax = self.data['p'].max()
                    num_samples = len(self.data['p'])
                except Exception as e:
                    pass

                                 
            rstr += '{: 8.2f}'.format(pmin) + sep
            rstr += '{: 8.2f}'.format(pmax) + sep
            rstr += '{: 6d}'.format(num_samples) + sep
            rstr += '{: 1d}'.format(int(self.baltic)) + sep            
            rstr += self.filename + sep
                
        return rstr


    def __str__(self):
        """
        String format
        """
        rstr = ""
        rstr += "pycnv of " + self.filename
        rstr += " at Lat: " + str(self.lat)
        rstr += ", Lon: " + str(self.lon)
        rstr += ", Date: " + datetime.datetime.strftime(self.date,'%Y-%m-%d %H:%M:%S')
        return rstr        
            
          
def test_pycnv():
    pycnv("/home/holterma/data/redox_drive/iow_data/fahrten.2011/06EZ1108.DTA/vCTD/DATA/cnv/0001_01.cnv")

# Main function
def main():
    sum_help = 'Gives a csv compatible summary'
    sumhead_help = 'Gives the header to the csv compatible summary'
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')    
    parser.add_argument('--summary', '-s', action='store_true', help=sum_help)
    parser.add_argument('--summary_header', '-sh', action='store_true', help=sumhead_help)
    parser.add_argument('--verbose', '-v', action='count')
    #parser.add_argument('--version', action='store_true')
    parser.add_argument('--version', action='version', version='%(prog)s ' + version)
    args = parser.parse_args()
    
    if(args.verbose == None):
        loglevel = logging.CRITICAL
    elif(args.verbose == 1):
        loglevel = logging.WARNING
    elif(args.verbose == 2):
        loglevel = logging.INFO        
    elif(args.verbose > 2):
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO


    logger.setLevel(loglevel)

    print(args.version)
    if(args.version != None):
        print(version)
    
    filename = args.filename

    print_summary = args.summary
    print_summary_header = args.summary_header
    
    if(filename != None):
        cnv = pycnv(filename,verbosity=loglevel)
        print(cnv)
    else:
        #logger.critical('Need a filename')
        print(parser.print_help())

    if(print_summary_header):
        summary = cnv._get_summary(header=True)
        print(summary)
    if(print_summary):
        summary = cnv._get_summary()
        print(summary)


#pc = pycnv("/home/holterma/data/redox_drive/iow_data/fahrten.2011/06EZ1108.DTA/vCTD/DATA/cnv/0001_01.cnv")
if __name__ == '__main__':
   main()
    

