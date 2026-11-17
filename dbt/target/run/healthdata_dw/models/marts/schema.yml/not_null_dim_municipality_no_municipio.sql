select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select no_municipio
from "healthdata_dw"."dw_gold"."dim_municipality"
where no_municipio is null



      
    ) dbt_internal_test